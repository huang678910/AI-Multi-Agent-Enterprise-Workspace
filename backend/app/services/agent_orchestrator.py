"""Agent Orchestrator - LangGraph multi-agent dispatch + WebSocket events"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.chat_service import ChatService
from app.agents.supervisor import AgentState, supervisor_node

logger = logging.getLogger(__name__)

AGENT_NODES = {}


def _ensure_nodes():
    """Ensure agent node functions are loaded"""
    if AGENT_NODES:
        return
    try:
        from app.agents.supervisor import (
            search_node, chat_node, research_node,
            analyst_node, writer_node, sql_node, profile_node, memory_node,
            ceo_node, finance_node, sales_node, hr_node,
            customer_node, operations_node, procurement_node,
        )
        AGENT_NODES["search"] = search_node
        AGENT_NODES["chat"] = chat_node
        AGENT_NODES["research"] = research_node
        AGENT_NODES["analyst"] = analyst_node
        AGENT_NODES["writer"] = writer_node
        AGENT_NODES["sql"] = sql_node
        AGENT_NODES["profile"] = profile_node
        AGENT_NODES["memory"] = memory_node
        AGENT_NODES["ceo"] = ceo_node
        AGENT_NODES["finance"] = finance_node
        AGENT_NODES["sales"] = sales_node
        AGENT_NODES["hr"] = hr_node
        AGENT_NODES["customer"] = customer_node
        AGENT_NODES["operations"] = operations_node
        AGENT_NODES["procurement"] = procurement_node
        logger.info(f"Agent nodes loaded: {list(AGENT_NODES.keys())}")
    except Exception as e:
        logger.error(f"Failed to load agent nodes: {e}", exc_info=True)


class AgentOrchestrator:

    def __init__(self, db: AsyncSession, workspace_id: str, user: User):
        self.db = db
        self.workspace_id = workspace_id
        self.user = user

    async def run_stream(self, session_id: str, message: str) -> AsyncGenerator[dict, None]:
        _ensure_nodes()

        chat_svc = ChatService(self.db)

        # 1. Save user message
        await chat_svc.save_message(session_id=session_id, role="user", content=message)

        # 2. Load history
        history = await chat_svc.list_messages(session_id)

        # 3. Build state
        state: AgentState = {
            "messages": [{"role": m.role.value, "content": m.content} for m in history[-20:]],
            "workspace_id": self.workspace_id,
            "session_id": session_id,
            "user_query": message,
            "next_agent": "supervisor",
            "next_agents": [],
            "context_text": "",
            "sources": [],
            "final_response": "",
            "agent_trace": [],
        }

        try:
            # 4. Supervisor routing - build agent pipeline
            yield {"type": "status", "content": "Planning agent pipeline...", "agent": "supervisor"}
            supervisor_result = await supervisor_node(state)
            state.update(supervisor_result)

            agent_pipeline = state.get("next_agents", ["chat"])
            if not agent_pipeline:
                agent_pipeline = ["chat"]

            pipeline_str = " -> ".join(agent_pipeline)
            yield {"type": "status", "content": f"Pipeline: {pipeline_str}", "agent": agent_pipeline[0]}

            # 5. Pre-populate RAG context (shared across all agents)
            if any(a in ("search", "research", "writer", "analyst", "chat", "profile") for a in agent_pipeline):
                yield {"type": "status", "content": "Searching knowledge base...", "agent": "search"}
                from app.database import AsyncSessionLocal
                from app.services.rag_service import RagService
                from app.agents.tools.web_search_tool import search_web

                sources = []
                context_text = ""
                try:
                    async with AsyncSessionLocal() as s:
                        results = await RagService(s).search(
                            query=message, workspace_id=self.workspace_id, top_k=5)
                        if results:
                            parts = [f"[Source: {r.filename}]\n{r.content}" for r in results]
                            sources = [{"filename": r.filename, "chunk_id": r.chunk_id, "similarity": r.similarity} for r in results]
                            context_text = "\n\n---\n\n".join(parts)
                            yield {"type": "status", "content": f"Found {len(results)} documents", "agent": "search"}
                except Exception as e:
                    logger.warning(f"RAG failed: {e}")

                try:
                    web_result = await search_web.ainvoke({"query": message, "max_results": 3})
                    if web_result and "not configured" not in web_result.lower() and "no results" not in web_result.lower():
                        context_text = (context_text + "\n\n### Web Results\n" + web_result) if context_text else ("### Web Results\n" + web_result)
                        yield {"type": "status", "content": "Web search completed", "agent": "search"}
                except Exception:
                    pass

                state["context_text"] = context_text
                state["sources"] = sources

            # 5.5. Pre-populate Memory context (parallel with RAG, non-blocking)
            try:
                yield {"type": "status", "content": "Recalling relevant memories...", "agent": "memory"}
                from app.database import AsyncSessionLocal as MemSessionLocal
                from app.services.memory_service import MemoryService
                from app.schemas.memory import RecallRequest
                async with MemSessionLocal() as s:
                    mem_svc = MemoryService(s, self.workspace_id)
                    memory_ctx = await mem_svc.get_context_for_dialog(message, top_k=3)
                    if memory_ctx:
                        existing = state.get("context_text", "")
                        state["context_text"] = memory_ctx + "\n\n" + existing if existing else memory_ctx
                        yield {"type": "status", "content": "Memory context loaded", "agent": "memory"}
            except Exception as e:
                logger.warning(f"Memory recall failed (non-blocking): {e}")

            # 5.6. Pre-populate Company Profile context (ALWAYS — core enterprise data)
            try:
                yield {"type": "status", "content": "Loading company profile...", "agent": "profile"}
                from app.database import AsyncSessionLocal as CoSessionLocal
                from app.services.company_service import CompanyService
                async with CoSessionLocal() as s:
                    co_svc = CompanyService(s, self.workspace_id)
                    company_ctx = await co_svc.get_company_summary()
                    if company_ctx:
                        existing = state.get("context_text", "")
                        state["context_text"] = ("### Enterprise Profile\n" + company_ctx + "\n\n" + existing) if existing else ("### Enterprise Profile\n" + company_ctx)
                        yield {"type": "status", "content": "Company profile loaded", "agent": "profile"}
            except Exception as e:
                logger.warning(f"Company profile load failed (non-blocking): {e}")

            # 5.7. Pre-populate document list + direct filename match
            try:
                from app.database import AsyncSessionLocal as DocListSession
                from sqlalchemy import select as sa_select
                from app.models.document import Document as DocModel
                from app.models.document_chunk import DocumentChunk as DcModel
                async with DocListSession() as s:
                    doc_result = await s.execute(
                        sa_select(DocModel.id, DocModel.filename, DocModel.file_type, DocModel.source_type)
                        .where(DocModel.workspace_id == self.workspace_id)
                        .order_by(DocModel.created_at.desc())
                        .limit(20)
                    )
                    docs = doc_result.all()
                    if docs:
                        doc_list = "\n".join(f"- [{d[3]}] {d[1]} ({d[2]})" for d in docs)
                        existing = state.get("context_text", "")
                        state["context_text"] = (existing + "\n\n### Available Documents\n" + doc_list) if existing else ("### Available Documents\n" + doc_list)

                        # Direct filename match: if user mentions a specific document name, inject its content
                        msg_lower = message.lower()
                        for d in docs:
                            doc_id, filename = d[0], d[1]
                            # Check if filename (or any part of it) appears in user message
                            if filename.lower() in msg_lower or any(
                                part in msg_lower for part in filename.lower().replace('.',' ').replace('_',' ').split()
                                if len(part) > 3
                            ):
                                chunk_result = await s.execute(
                                    sa_select(DcModel.content)
                                    .where(DcModel.document_id == doc_id)
                                    .order_by(DcModel.chunk_index)
                                    .limit(5)
                                )
                                chunks = chunk_result.scalars().all()
                                if chunks:
                                    full_text = "\n\n---\n\n".join(chunks)
                                    existing2 = state.get("context_text", "")
                                    state["context_text"] = existing2 + f"\n\n### Document Content: {filename}\n{full_text[:3000]}"
                                    yield {"type": "status", "content": f"Loaded document: {filename}", "agent": "search"}
                                    break  # Only inject one matched document
            except Exception as e:
                logger.warning(f"Document list load failed (non-blocking): {e}")

            # 5.8. Pre-populate Digital Twin metrics context (for department agents)
            try:
                yield {"type": "status", "content": "Loading business metrics...", "agent": "search"}
                from app.database import AsyncSessionLocal as MetricsSessionLocal
                from app.services.business_metrics_service import BusinessMetricsService
                async with MetricsSessionLocal() as s:
                    metrics_svc = BusinessMetricsService(s)
                    metrics_ctx = await metrics_svc.get_ai_analysis_context(self.workspace_id)
                    if metrics_ctx:
                        existing = state.get("context_text", "")
                        state["context_text"] = metrics_ctx + "\n\n" + existing if existing else metrics_ctx
                        yield {"type": "status", "content": "Business metrics loaded", "agent": "search"}
            except Exception as e:
                logger.warning(f"Business metrics load failed (non-blocking): {e}")

            # 6. Execute agent pipeline - loop over agents in sequence
            for i, agent_name in enumerate(agent_pipeline):
                node_fn = AGENT_NODES.get(agent_name)
                if not node_fn:
                    logger.warning(f"Agent not found: {agent_name}, skipping")
                    continue

                yield {"type": "status", "content": f"Running: {agent_name} ({i+1}/{len(agent_pipeline)})", "agent": agent_name}

                # Pass previous agent's output as context for next agent
                if i > 0 and state.get("final_response"):
                    state["context_text"] = (state.get("context_text", "") + "\n\n### Previous Agent Output\n" + state["final_response"])

                logger.info(f"Pipeline step {i+1}/{len(agent_pipeline)}: executing {agent_name}")
                agent_result = await node_fn(state)
                state.update(agent_result)

                # Auto-save reports from writer agent
                if agent_name == "writer" and state.get("final_response"):
                    try:
                        from app.models.report import Report
                        from app.services.export_service import export_markdown
                        import uuid as uuid_mod
                        report_title = message[:100] if len(message) <= 100 else message[:97] + "..."
                        report = Report(workspace_id=self.workspace_id, title=report_title,
                                      content=state["final_response"], format="markdown")
                        self.db.add(report)
                        await self.db.flush()
                        safe_name = f"report_{uuid_mod.uuid4().hex[:8]}"
                        report.file_path = export_markdown(state["final_response"], safe_name)
                        await self.db.flush()
                        dl_url = f"/api/v1/workspaces/{self.workspace_id}/reports/{report.id}/download"
                        state["final_response"] += f"\n\n---\n\n📄 **Report saved!** [Download]({dl_url})"
                    except Exception as ex:
                        logger.error(f"Auto-save report failed: {ex}")

            # 7. Stream final response from last agent
            full_response = state.get("final_response", "")
            sources = state.get("sources", [])

            if full_response:
                chunk_size = 3
                for i in range(0, len(full_response), chunk_size):
                    yield {"type": "token", "content": full_response[i:i+chunk_size]}
            else:
                yield {"type": "token", "content": "No response generated."}

            # 8. Save reply
            try:
                await chat_svc.save_message(
                    session_id=session_id, role="assistant",
                    content=full_response, sources=sources)
                if len(history) <= 2:
                    title = message[:50] + ("..." if len(message) > 50 else "")
                    await chat_svc.update_session_title(session_id, title)
                await self.db.commit()
            except Exception as e:
                logger.error(f"Failed to save reply: {e}")

            # 8.5. Extract memories from conversation (non-blocking)
            if full_response and len(full_response) > 50:
                try:
                    from app.database import AsyncSessionLocal as ExSessionLocal
                    from app.services.memory_service import MemoryService
                    async with ExSessionLocal() as s:
                        mem_svc = MemoryService(s, self.workspace_id)
                        await mem_svc.extract_from_conversation(message, full_response, session_id)
                        await s.commit()  # ← CRITICAL: AsyncSessionLocal does NOT auto-commit!
                except Exception as e:
                    logger.warning(f"Memory extraction failed (non-blocking): {e}")

            yield {"type": "done", "content": full_response, "sources": sources}

        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            yield {"type": "error", "content": str(e)}
