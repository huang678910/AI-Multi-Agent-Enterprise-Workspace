"""Research Agent — Deep Research"""

import logging
from datetime import datetime, timezone
from langchain_core.messages import SystemMessage, HumanMessage

from app.services.llm_service import _get_llm
from app.agents.tools.web_search_tool import search_web
from app.agents.tools.rag_tool import search_knowledge_base

logger = logging.getLogger(__name__)

RESEARCH_SYSTEM_PROMPT = f"""You are a deep research specialist. The current date is {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.
Conduct thorough research synthesizing all available sources.

Process:
1. Analyze the research question deeply
2. Identify key themes and sub-topics from the provided information
3. Cross-reference knowledge base findings with web search results
4. Identify gaps, contradictions, and areas needing further investigation
5. Synthesize into a comprehensive research report

Output format:
- **Executive Summary** (2-3 sentences)
- **Key Findings** (bullet points)
- **Detailed Analysis** (organized by sub-topic)
- **Information Gaps** (what's missing)
- **Conclusions & Recommendations**
- **Sources** (cite all sources)
"""


async def run_research_agent(
    query: str,
    knowledge_context: str = "",
    workspace_id: str = "",
    web_context: str = "",
) -> dict:
    """Research Agent：深度多步研究

    Args:
        query: 研究问题
        knowledge_context: 知识库搜索结果（如果已提供）
        workspace_id: 工作区 ID
        web_context: 联网搜索结果（如果已提供）
    """
    logger.info(f"ResearchAgent: researching '{query[:80]}...'")

    # 1. 如果未提供上下文，自己搜索
    kb_text = knowledge_context
    if not kb_text and workspace_id:
        try:
            kb_text = await search_knowledge_base.ainvoke({
                "query": query, "workspace_id": workspace_id, "top_k": 5})
        except Exception as e:
            logger.warning(f"KB search failed: {e}")

    # 2. 联网搜索
    web_text = web_context
    if not web_text:
        try:
            web_result = await search_web.ainvoke({"query": query, "max_results": 5})
            if web_result and "not configured" not in web_result.lower():
                web_text = web_result
        except Exception as e:
            logger.debug(f"Web search skipped: {e}")

    # 3. 构建综合上下文
    parts = []
    if kb_text and "No relevant" not in kb_text:
        parts.append(f"### Knowledge Base Results\n{kb_text}")
    if web_text:
        parts.append(f"### Web Search Results\n{web_text}")

    combined = "\n\n".join(parts) if parts else "No information available."

    # 4. LLM 深度研究
    messages = [
        SystemMessage(content=RESEARCH_SYSTEM_PROMPT),
        HumanMessage(content=f"Research Question: {query}\n\nAvailable Information:\n{combined}"),
    ]

    llm = _get_llm(streaming=True)
    full_response = ""
    async for chunk in llm.astream(messages):
        if chunk.content:
            full_response += chunk.content

    return {
        "final_response": full_response,
        "sources": [],
        "agent_trace": ["research"],
    }
