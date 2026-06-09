"""Memory Agent — 记忆检索与上下文增强"""

import logging
from datetime import datetime, timezone

from app.services.llm_service import _get_llm
from app.database import AsyncSessionLocal
from app.services.memory_service import MemoryService
from app.schemas.memory import RecallRequest

logger = logging.getLogger(__name__)

MEMORY_SYSTEM_PROMPT = f"""You are the Enterprise Memory Agent.
Your job is to answer questions using the company's stored memories and past events.
The current date is: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.

Rules:
1. Answer based on the provided memories. If no relevant memories exist, say so honestly.
2. Cite specific events and facts from the memories when possible.
3. Distinguish between: long-term knowledge, episodic events (dated), and semantic facts (relationships).
4. ALWAYS use the current date — NEVER make up dates."""


async def run_memory_agent(
    query: str,
    workspace_id: str,
    context_text: str = "",
) -> dict:
    """Search and synthesize enterprise memories

    Args:
        query: User's question
        workspace_id: Workspace UUID
        context_text: Additional context from RAG or previous agents

    Returns:
        {"final_response": str, "agent_trace": list[str]}
    """
    # Recall relevant memories
    memory_context = ""
    memories_found = 0
    try:
        async with AsyncSessionLocal() as s:
            svc = MemoryService(s, workspace_id)
            results = await svc.recall(RecallRequest(query=query, top_k=5))
            if results:
                memories_found = len(results)
                parts = ["### Enterprise Memories"]
                for r in results:
                    parts.append(f"- [{r.memory_type}] {r.title} (importance: {r.importance})\n  {r.content[:300]}")
                memory_context = "\n\n".join(parts)
    except Exception as e:
        logger.warning(f"Memory recall failed: {e}")

    if not memory_context and not context_text:
        return {
            "final_response": "I don't have any stored memories or context about that. You can create memories by having conversations — I'll automatically remember important facts about your enterprise. Or manually add memories from the **Memories** page.",
            "agent_trace": ["memory: no_data"],
        }

    # Build full context
    full_context = memory_context
    if context_text:
        full_context += f"\n\n### Additional Context\n{context_text}"

    # LLM synthesis
    try:
        llm = _get_llm(streaming=False)
        from langchain_core.messages import SystemMessage, HumanMessage

        messages = [
            SystemMessage(content=MEMORY_SYSTEM_PROMPT),
            HumanMessage(content=f"Context:\n{full_context}\n\nUser Question: {query}"),
        ]
        response = await llm.ainvoke(messages)
        return {
            "final_response": response.content.strip(),
            "agent_trace": [f"memory: synthesized from {memories_found} memories"],
        }
    except Exception as e:
        logger.error(f"Memory agent LLM failed: {e}")
        if memory_context:
            return {
                "final_response": f"Here's what I found in the company's memory:\n\n{memory_context}",
                "agent_trace": [f"memory: raw_data_fallback, {memories_found} results"],
            }
        return {
            "final_response": "Unable to retrieve memories at this time.",
            "agent_trace": ["memory: error"],
        }
