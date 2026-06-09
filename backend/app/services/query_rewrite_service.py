"""Query Rewrite 服务 — 使用 LLM 将口语化查询改写为检索优化查询"""

import logging

logger = logging.getLogger(__name__)

REWRITE_SYSTEM_PROMPT = """You are a query optimization specialist. Your task is to rewrite user questions into optimized search queries.

Rules:
1. Extract key concepts, entities, and technical terms
2. Remove filler words and conversational language
3. Add relevant synonyms and related terms
4. Keep the original intent intact
5. Output ONLY the rewritten query, no explanation

Examples:
User: "那个支付的东西最近改了啥"
Rewritten: "支付系统 变更 改动 最近更新 payment system changes"

User: "hello how are you"
Rewritten: "greeting" (keep as-is for non-search queries)

User: "Q2 报告中关于营收的部分有什么关键数据"
Rewritten: "Q2 report revenue key metrics financial data 营收 收入 关键数据"
"""


async def rewrite_query(user_query: str) -> str:
    """用 LLM 重写用户查询以提高检索质量

    Args:
        user_query: 原始用户输入

    Returns:
        优化后的搜索查询
    """
    # 短查询不需要改写
    if len(user_query) < 10:
        return user_query

    try:
        from app.services.llm_service import _get_llm
        from langchain_core.messages import SystemMessage, HumanMessage
        llm = _get_llm(streaming=False)
        messages = [
            SystemMessage(content=REWRITE_SYSTEM_PROMPT),
            HumanMessage(content=user_query),
        ]
        response = await llm.ainvoke(messages)
        rewritten = response.content.strip()

        # 如果 LLM 返回了多余内容（如带引号），清理一下
        if len(rewritten) > len(user_query) * 3:
            logger.warning(f"Query rewrite too long, using original: {user_query[:50]}...")
            return user_query

        logger.debug(f"Query rewritten: '{user_query[:50]}...' -> '{rewritten[:50]}...'")
        return rewritten or user_query

    except Exception as e:
        logger.warning(f"Query rewrite failed, using original: {e}")
        return user_query
