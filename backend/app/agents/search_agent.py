"""Search Agent — RAG + Web Search + LLM synthesis"""

import logging
from datetime import datetime, timezone
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.tools.rag_tool import search_knowledge_base
from app.agents.tools.web_search_tool import search_web
from app.services.llm_service import _get_llm

logger = logging.getLogger(__name__)

SEARCH_AGENT_PROMPT = f"""You are a knowledge retrieval specialist. The current date is {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.
Answer user questions based on search results from both the knowledge base and the web.

Instructions:
- Use knowledge base results first (internal documents)
- Supplement with web search results when needed
- Always cite sources: [Source: filename] for documents, [Web: title] for web
- If neither source has enough information, say so honestly
- Be concise and well-structured. Use Markdown."""


async def run_search_agent(query: str, workspace_id: str, top_k: int = 5, context_text: str = "") -> dict:
    """执行搜索智能体：知识库搜索 + 联网搜索 + LLM 合成"""
    logger.info(f"SearchAgent: searching '{query[:80]}...'")

    # 1. 知识库搜索
    kb_context = ""
    if context_text:
        kb_context = context_text
    else:
        kb_context = await search_knowledge_base.ainvoke({
            "query": query, "workspace_id": workspace_id, "top_k": top_k})

    # 2. 联网搜索（尽力而为）
    web_context = ""
    try:
        web_result = await search_web.ainvoke({"query": query, "max_results": 3})
        if web_result and "not configured" not in web_result.lower() and "no results" not in web_result.lower():
            web_context = web_result
    except Exception:
        pass

    # 3. 构建上下文
    combined = kb_context or ""
    if web_context and "Search error" not in web_context:
        combined += f"\n\n### Web Search Results\n{web_context}" if combined else web_context

    # 4. LLM 合成
    messages = [
        SystemMessage(content=SEARCH_AGENT_PROMPT),
        SystemMessage(content=f"Search results:\n\n{combined}" if combined else "No search results available."),
        HumanMessage(content=query),
    ]

    llm = _get_llm(streaming=True)
    full_response = ""
    async for chunk in llm.astream(messages):
        if chunk.content:
            full_response += chunk.content

    return {
        "final_response": full_response,
        "sources": [],
        "context_text": combined,
        "agent_trace": ["search"],
    }
