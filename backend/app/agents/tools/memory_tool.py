"""Memory Tool — save / recall enterprise memories via Tool Registry"""

import logging
from langchain_core.tools import tool

from app.database import AsyncSessionLocal
from app.services.memory_service import MemoryService
from app.schemas.memory import MemoryCreate, RecallRequest

logger = logging.getLogger(__name__)


@tool
async def save_memory(
    title: str,
    content: str,
    workspace_id: str,
    memory_type: str = "long_term",
    importance: float = 5.0,
    entity_type: str | None = None,
) -> str:
    """Save an important fact or event to enterprise memory.

    Use this when:
    - A user shares strategic information about the company
    - An important decision has been made
    - A key fact about the business is revealed
    - Historical context that should be remembered for future conversations

    Args:
        title: Short title for the memory
        content: Detailed content to remember
        workspace_id: Current workspace UUID
        memory_type: 'long_term' (general), 'episodic' (dated event), or 'semantic' (factual relationship)
        importance: 1-10 scale, higher = more important
        entity_type: Optional associated entity (e.g. 'department', 'product')
    """
    try:
        async with AsyncSessionLocal() as s:
            svc = MemoryService(s, workspace_id)
            memory = await svc.create_memory(MemoryCreate(
                memory_type=memory_type,
                title=title,
                content=content,
                importance=min(10, max(1, importance)),
                entity_type=entity_type,
            ))
            return f"Memory saved: {memory.title} (id: {memory.id})"
    except Exception as e:
        logger.error(f"save_memory failed: {e}")
        return f"Failed to save memory: {e}"


@tool
async def recall_memory(query: str, workspace_id: str, top_k: int = 5) -> str:
    """Recall relevant enterprise memories using semantic search.

    Use this when:
    - A user asks about past events, decisions, or company facts
    - Context from previous conversations would help answer the current question
    - You need to know what the company has discussed before

    Args:
        query: Natural language search query
        workspace_id: Current workspace UUID
        top_k: Number of memories to retrieve (default 5)
    """
    try:
        async with AsyncSessionLocal() as s:
            svc = MemoryService(s, workspace_id)
            results = await svc.recall(RecallRequest(query=query, top_k=top_k))
            if not results:
                return "No relevant memories found."
            parts = ["### Recalled Memories"]
            for r in results:
                parts.append(f"- [{r.memory_type}] {r.title}: {r.content[:200]} (importance: {r.importance}, score: {r.similarity})")
            return "\n".join(parts)
    except Exception as e:
        logger.error(f"recall_memory failed: {e}")
        return f"Failed to recall memories: {e}"
