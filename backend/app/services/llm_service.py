"""LLM 服务 — LangChain + DeepSeek 流式调用"""

import json
import logging
import traceback
from typing import AsyncGenerator

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.message import Message
from app.services.rag_service import RagService
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)
settings = get_settings()

# LangChain ChatOpenAI 实例（DeepSeek API 兼容）
_llm = None


def _get_llm(streaming: bool = True) -> ChatOpenAI:
    """获取 LangChain ChatOpenAI 实例（单例）"""
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            temperature=0.7,
            max_tokens=2048,
            streaming=streaming,
        )
    else:
        # 切换 streaming 模式
        _llm.streaming = streaming
    return _llm


from datetime import datetime, timezone

def _get_current_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC (%A)")

SYSTEM_PROMPT = f"""You are an AI assistant for an enterprise knowledge workspace.
The current date and time is: {_get_current_date()}

Your task is to answer user questions using ALL available enterprise context:
1. Enterprise Profile — Company info, departments, employees, products, customers, KPIs
2. Documents — Uploaded files and knowledge base content
3. Enterprise Memory — Past decisions, events, and company facts
4. Web Search Results — Real-time internet information

Instructions:
- You KNOW the current date: {_get_current_date()}. Always use THIS date, never make up dates.
- Use ALL context types to give comprehensive answers
- When asked about the company, products, departments, or employees, ALWAYS reference the Enterprise Profile
- Cite document sources by filename in [brackets]
- If context doesn't contain the answer, say so and provide your best general knowledge
- Keep answers concise and well-structured with Markdown formatting"""


class LLMService:

    async def stream_chat(
        self,
        messages: list[Message],
        workspace_id: str,
        session_id: str,
    ) -> AsyncGenerator[str, None]:
        """SSE 流式对话（兼容旧 SSE 端点）"""

        yield self._sse("start", {"content": "Connected"})

        try:
            # 1. 找到最新的用户消息
            user_msg = None
            for m in reversed(messages):
                if m.role.value == "user":
                    user_msg = m
                    break

            if not user_msg:
                yield self._sse("error", {"content": "No message found"})
                yield self._sse("done", {"content": ""})
                return

            # 2. RAG 搜索（尽力而为，失败不阻止对话）
            sources = []
            context = ""
            try:
                async with AsyncSessionLocal() as s:
                    results = await RagService(s).search(
                        query=user_msg.content,
                        workspace_id=workspace_id,
                        top_k=5,
                    )
                    if results:
                        parts = []
                        for r in results:
                            parts.append(f"[Source: {r.filename}]\n{r.content}")
                            sources.append({
                                "filename": r.filename,
                                "chunk_id": r.chunk_id,
                                "similarity": r.similarity,
                            })
                        context = "\n\n---\n\n".join(parts)
            except Exception as e:
                logger.warning(f"RAG skipped: {e}")

            # 3. 构建 LangChain 消息
            lc_messages = [SystemMessage(content=SYSTEM_PROMPT)]
            if context:
                lc_messages.append(SystemMessage(
                    content=f"Enterprise Context (Company Profile + Documents + Memory + Web):\n\n{context}"
                ))
            for m in messages[-20:]:
                role = m.role.value
                if role == "user":
                    lc_messages.append(HumanMessage(content=m.content))
                elif role == "assistant":
                    lc_messages.append(AIMessage(content=m.content))
                else:
                    lc_messages.append(SystemMessage(content=m.content))

            # 4. 调用 LangChain ChatOpenAI 流式
            llm = _get_llm(streaming=True)
            logger.info(f"Calling {settings.LLM_MODEL} with {len(lc_messages)} messages")

            yield self._sse("status", {"content": "Generating..."})

            full = ""
            async for chunk in llm.astream(lc_messages):
                if chunk.content:
                    full += chunk.content
                    yield self._sse("token", {"content": chunk.content})

            # 5. 保存助手回复
            try:
                async with AsyncSessionLocal() as s:
                    svc = ChatService(s)
                    await svc.save_message(
                        session_id=session_id, role="assistant",
                        content=full, sources=sources,
                    )
                    if len(messages) <= 2:
                        title = user_msg.content[:50]
                        if len(user_msg.content) > 50:
                            title += "..."
                        await svc.update_session_title(session_id, title)
                    await s.commit()
            except Exception as e:
                logger.error(f"Failed to save reply: {e}")

            yield self._sse("done", {"content": "", "sources": sources})

        except Exception as e:
            logger.error(f"Stream error: {e}\n{traceback.format_exc()}")
            yield self._sse("error", {"content": str(e)})
            yield self._sse("done", {"content": ""})

    async def stream_chat_dict(
        self,
        messages: list[Message],
        workspace_id: str,
        session_id: str,
    ) -> AsyncGenerator[dict, None]:
        """WebSocket 流式对话 — 产出 dict 事件（供 AgentOrchestrator 复用）"""

        yield {"type": "start", "content": "Connected"}

        try:
            # 1. 找到最新的用户消息
            user_msg = None
            for m in reversed(messages):
                if m.role.value == "user":
                    user_msg = m
                    break

            if not user_msg:
                yield {"type": "error", "content": "No message found"}
                return

            # 2. RAG 搜索
            sources = []
            context = ""
            try:
                async with AsyncSessionLocal() as s:
                    results = await RagService(s).search(
                        query=user_msg.content,
                        workspace_id=workspace_id,
                        top_k=5,
                    )
                    if results:
                        parts = []
                        for r in results:
                            parts.append(f"[Source: {r.filename}]\n{r.content}")
                            sources.append({
                                "filename": r.filename,
                                "chunk_id": r.chunk_id,
                                "similarity": r.similarity,
                            })
                        context = "\n\n---\n\n".join(parts)
            except Exception as e:
                logger.warning(f"RAG skipped: {e}")

            # 3. 构建 LangChain 消息
            lc_messages = [SystemMessage(content=SYSTEM_PROMPT)]
            if context:
                lc_messages.append(SystemMessage(
                    content=f"Enterprise Context (Company Profile + Documents + Memory + Web):\n\n{context}"
                ))
            for m in messages[-20:]:
                role = m.role.value
                if role == "user":
                    lc_messages.append(HumanMessage(content=m.content))
                elif role == "assistant":
                    lc_messages.append(AIMessage(content=m.content))
                else:
                    lc_messages.append(SystemMessage(content=m.content))

            # 4. 流式调用
            llm = _get_llm(streaming=True)
            logger.info(f"[WS] Calling {settings.LLM_MODEL} with {len(lc_messages)} messages")

            full = ""
            async for chunk in llm.astream(lc_messages):
                if chunk.content:
                    full += chunk.content
                    yield {"type": "token", "content": chunk.content}

            # 5. 保存
            try:
                async with AsyncSessionLocal() as s:
                    svc = ChatService(s)
                    await svc.save_message(
                        session_id=session_id, role="assistant",
                        content=full, sources=sources,
                    )
                    if len(messages) <= 2:
                        title = user_msg.content[:50]
                        if len(user_msg.content) > 50:
                            title += "..."
                        await svc.update_session_title(session_id, title)
                    await s.commit()
            except Exception as e:
                logger.error(f"Failed to save reply: {e}")

            yield {"type": "done", "content": full, "sources": sources}

        except Exception as e:
            logger.error(f"Stream error: {e}\n{traceback.format_exc()}")
            yield {"type": "error", "content": str(e)}

    @staticmethod
    def _sse(event_type: str, data: dict) -> str:
        return f"data: {json.dumps({'type': event_type, **data})}\n\n"
