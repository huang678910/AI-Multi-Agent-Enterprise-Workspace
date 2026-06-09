"""企业记忆系统 — CRUD + 向量检索 + 衰减 + 自动提取"""

import uuid
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, delete, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enterprise_memory import EnterpriseMemory, MemoryEvent
from app.schemas.memory import (
    MemoryCreate, MemoryUpdate, RecallRequest, RecallResult,
    EventCreate, EventUpdate,
)

logger = logging.getLogger(__name__)


class MemoryService:

    def __init__(self, db: AsyncSession, workspace_id: str):
        self.db = db
        self.workspace_id = uuid.UUID(workspace_id)

    # ─── Memories CRUD ─────────────────────────────────

    async def list_memories(
        self,
        memory_type: str | None = None,
        entity_type: str | None = None,
        min_importance: float | None = None,
    ) -> list[EnterpriseMemory]:
        stmt = select(EnterpriseMemory).where(EnterpriseMemory.workspace_id == self.workspace_id)
        if memory_type:
            stmt = stmt.where(EnterpriseMemory.memory_type == memory_type)
        if entity_type:
            stmt = stmt.where(EnterpriseMemory.entity_type == entity_type)
        if min_importance is not None:
            stmt = stmt.where(EnterpriseMemory.importance >= min_importance)
        stmt = stmt.order_by(EnterpriseMemory.importance.desc(), EnterpriseMemory.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_memory(self, data: MemoryCreate) -> EnterpriseMemory:
        memory = EnterpriseMemory(
            workspace_id=self.workspace_id,
            memory_type=data.memory_type,
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            title=data.title,
            content=data.content,
            importance=data.importance,
            source_session_id=data.source_session_id,
            source_message_id=data.source_message_id,
            extra_data=data.extra_data,
        )
        # Generate embedding for semantic search
        try:
            from app.services.embedding_service import embed_single
            memory.embedding = await embed_single(data.content)
        except Exception as e:
            logger.warning(f"Memory embedding generation failed (non-blocking): {e}")

        self.db.add(memory)
        await self.db.flush()
        await self.db.refresh(memory)

        # Auto-create event for episodic/important memories
        if data.memory_type == "episodic" and data.importance >= 5:
            event = MemoryEvent(
                workspace_id=self.workspace_id,
                title=data.title,
                description=data.content[:500],
                impact="neutral",
                tags=[data.memory_type],
            )
            self.db.add(event)
            await self.db.flush()

        return memory

    async def update_memory(self, memory_id: str, data: MemoryUpdate) -> EnterpriseMemory:
        memory = await self._get_memory(memory_id)
        update_dict = data.model_dump(exclude_unset=True)
        for k, v in update_dict.items():
            setattr(memory, k, v)

        # Re-generate embedding if content changed
        if "content" in update_dict:
            try:
                from app.services.embedding_service import embed_single
                memory.embedding = await embed_single(memory.content)
            except Exception as e:
                logger.warning(f"Memory re-embedding failed: {e}")

        await self.db.flush()
        await self.db.refresh(memory)
        return memory

    async def delete_memory(self, memory_id: str) -> None:
        memory = await self._get_memory(memory_id)
        await self.db.delete(memory)
        await self.db.flush()

    async def _get_memory(self, memory_id: str) -> EnterpriseMemory:
        result = await self.db.execute(
            select(EnterpriseMemory).where(
                EnterpriseMemory.id == uuid.UUID(memory_id),
                EnterpriseMemory.workspace_id == self.workspace_id,
            )
        )
        memory = result.scalar_one_or_none()
        if not memory:
            raise ValueError("Memory not found")
        return memory

    # ─── Semantic Recall ───────────────────────────────

    async def recall(self, req: RecallRequest) -> list[RecallResult]:
        """语义检索记忆 — 向量搜索 + importance × recency 排序"""
        # Generate query embedding
        embedding = None
        try:
            from app.services.embedding_service import embed_single
            embedding = await embed_single(req.query)
        except Exception as e:
            logger.warning(f"Recall embedding failed: {e}")

        results = []
        if embedding:
            # Vector search
            stmt = (
                select(EnterpriseMemory)
                .where(EnterpriseMemory.workspace_id == self.workspace_id)
            )
            if req.memory_type:
                stmt = stmt.where(EnterpriseMemory.memory_type == req.memory_type)
            # Order by cosine distance
            stmt = stmt.order_by(
                EnterpriseMemory.embedding.cosine_distance(embedding)
            ).limit(req.top_k * 3)  # Get more candidates for re-ranking

            result = await self.db.execute(stmt)
            candidates = result.scalars().all()

            # Re-rank: importance × recency
            now = datetime.now(timezone.utc)
            scored = []
            for m in candidates:
                # Cosine similarity = 1 - distance, but we already sorted by distance
                # Weighted score: importance (40%) + recency (30%) + vector (30%)
                recency_score = 1.0
                if m.last_recalled_at:
                    days_since = (now - m.last_recalled_at).days
                    recency_score = max(0.1, 1.0 - days_since / 90.0)  # Decay over 90 days
                # Approximate similarity from position (first = highest)
                vector_score = 1.0 - (candidates.index(m) / max(len(candidates), 1))
                combined = (m.importance / 10.0) * 0.4 + recency_score * 0.3 + vector_score * 0.3
                scored.append((m, combined))

            scored.sort(key=lambda x: x[1], reverse=True)
            top = scored[:req.top_k]

            for memory, score in top:
                # Update access stats
                memory.access_count = (memory.access_count or 0) + 1
                memory.last_recalled_at = now
                results.append(RecallResult(
                    id=memory.id,
                    title=memory.title,
                    content=memory.content,
                    memory_type=memory.memory_type,
                    importance=memory.importance,
                    similarity=round(score, 4),
                    created_at=memory.created_at,
                ))

            if top:
                await self.db.flush()

        return results

    async def get_context_for_dialog(self, query: str, top_k: int = 3) -> str:
        """Get relevant memories as context string for agent dialog"""
        memories = await self.recall(RecallRequest(query=query, top_k=top_k))
        if not memories:
            return ""

        parts = ["### Enterprise Memory (relevant past knowledge)"]
        for m in memories:
            parts.append(f"- [{m.memory_type}] {m.title}: {m.content[:300]}")
        return "\n".join(parts)

    # ─── Decay (衰减) ──────────────────────────────────

    async def apply_decay(self) -> int:
        """降低长期未访问记忆的重要性评分。返回受影响的记忆数量"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        stmt = (
            update(EnterpriseMemory)
            .where(
                EnterpriseMemory.workspace_id == self.workspace_id,
                EnterpriseMemory.last_recalled_at < cutoff,
                EnterpriseMemory.importance > 1.0,
            )
            .values(importance=EnterpriseMemory.importance - 0.5)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        affected = result.rowcount
        if affected:
            logger.info(f"Memory decay applied to {affected} memories in workspace {self.workspace_id}")
        return affected

    # ─── Auto-Extract from Conversation ────────────────

    async def extract_from_conversation(self, user_msg: str, assistant_msg: str, session_id: str) -> list[EnterpriseMemory]:
        """使用 LLM 从对话中自动提取值得记忆的内容"""
        try:
            from app.services.llm_service import _get_llm
            from langchain_core.messages import SystemMessage, HumanMessage

            llm = _get_llm(streaming=False)
            prompt = f"""Analyze this conversation and extract any facts worth remembering about the enterprise.
Return a JSON array of memories. Each memory must have: title, content, memory_type ("long_term", "episodic", or "semantic"), importance (1-10).

Rules:
- Only extract FACTS about the company, not personal opinions or greetings
- Importance: 8-10 for strategic decisions/events, 5-7 for operational facts, 1-4 for trivial info
- If nothing is worth remembering, return empty array []
- memory_type: "episodic" for dated events, "semantic" for factual relationships, "long_term" for general knowledge

User: {user_msg[:500]}
Assistant: {assistant_msg[:1000]}

Return ONLY the JSON array, no markdown, no code blocks."""

            response = await llm.ainvoke([
                SystemMessage(content="You extract enterprise memories from conversations. Return only valid JSON arrays."),
                HumanMessage(content=prompt),
            ])

            text = response.content.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            import json as json_mod
            items = json_mod.loads(text)
            if not isinstance(items, list):
                items = []

            created = []
            for item in items[:5]:  # Max 5 per extraction
                try:
                    memory = await self.create_memory(MemoryCreate(
                        memory_type=item.get("memory_type", "long_term"),
                        title=item.get("title", "Untitled")[:500],
                        content=item.get("content", "")[:2000],
                        importance=float(item.get("importance", 5)),
                        source_session_id=uuid.UUID(session_id) if session_id else None,
                    ))
                    created.append(memory)
                except Exception as e:
                    logger.warning(f"Failed to save extracted memory: {e}")
                    continue

            if created:
                logger.info(f"Extracted {len(created)} memories from conversation in session {session_id}")
            return created

        except Exception as e:
            logger.warning(f"Memory extraction failed (non-blocking): {e}")
            return []

    # ─── Events CRUD ───────────────────────────────────

    async def list_events(self) -> list[MemoryEvent]:
        stmt = (
            select(MemoryEvent)
            .where(MemoryEvent.workspace_id == self.workspace_id)
            .order_by(MemoryEvent.event_date.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_event(self, data: EventCreate) -> MemoryEvent:
        event = MemoryEvent(
            workspace_id=self.workspace_id,
            title=data.title,
            description=data.description,
            event_date=data.event_date,
            related_entities=data.related_entities,
            impact=data.impact,
            tags=data.tags,
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def delete_event(self, event_id: str) -> None:
        result = await self.db.execute(
            select(MemoryEvent).where(
                MemoryEvent.id == uuid.UUID(event_id),
                MemoryEvent.workspace_id == self.workspace_id,
            )
        )
        event = result.scalar_one_or_none()
        if not event:
            raise ValueError("Event not found")
        await self.db.delete(event)
        await self.db.flush()
