"""聊天智能体节点 — 通用对话"""

import logging
from typing import TypedDict

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.services.llm_service import _get_llm, SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class ChatAgentInput(TypedDict, total=False):
    messages: list  # 历史消息 (dicts with role/content)
    user_query: str


async def run_chat_agent(messages: list, user_query: str, context_text: str = "") -> dict:
    """执行聊天智能体：通用 AI 对话

    Returns:
        dict with keys: final_response, agent_trace
    """
    logger.info(f"ChatAgent: responding to '{user_query[:80]}...'")

    # 1. 构建 LangChain 消息
    lc_messages = [SystemMessage(content=SYSTEM_PROMPT)]
    if context_text:
        lc_messages.append(SystemMessage(content=f"Enterprise Context:\n\n{context_text}"))

    # 添加历史消息（最近 20 条）
    for m in messages[-20:]:
        role = m.get("role", "") if isinstance(m, dict) else getattr(m, "role", "")
        content = m.get("content", "") if isinstance(m, dict) else getattr(m, "content", "")
        if role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))

    # 确保最后是用户消息
    if not lc_messages or not isinstance(lc_messages[-1], HumanMessage):
        lc_messages.append(HumanMessage(content=user_query))

    # 2. 调用 LLM 流式
    llm = _get_llm(streaming=True)
    full_response = ""
    async for chunk in llm.astream(lc_messages):
        if chunk.content:
            full_response += chunk.content

    return {
        "final_response": full_response,
        "sources": [],
        "context_text": "",
        "agent_trace": ["chat"],
    }
