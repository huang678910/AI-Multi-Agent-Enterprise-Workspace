"""聊天 API — 会话管理 + SSE 流式对话 + HTTP 降级"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.api.deps import get_current_user, require_workspace_role
from app.models.user import User
from app.models.chat_session import ChatSession
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionListResponse,
    MessageResponse,
    ChatStreamRequest,
)
from app.services.chat_service import ChatService
from app.services.llm_service import LLMService
from app.core.exceptions import NotFoundException, ForbiddenException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces/{workspace_id}/chat", tags=["Chat"])


@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_sessions(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出当前工作区中当前用户的会话"""
    await require_workspace_role(workspace_id, current_user, "viewer", db)
    sessions = await ChatService(db).list_sessions(workspace_id, current_user.id)
    return ChatSessionListResponse(
        sessions=[ChatSessionResponse.model_validate(s) for s in sessions],
        total=len(sessions),
    )


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
async def create_session(
    workspace_id: str,
    request: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建新会话"""
    await require_workspace_role(workspace_id, current_user, "member", db)
    session = await ChatService(db).create_session(workspace_id, current_user.id, request.title)
    return ChatSessionResponse.model_validate(session)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    workspace_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除会话（仅会话所有者或 admin 可操作）"""
    await require_workspace_role(workspace_id, current_user, "viewer", db)
    # 验证会话属于当前用户或用户是 admin
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundException("Chat session not found")
    if str(session.user_id) != str(current_user.id):
        # 非所有者需要 admin 权限
        await require_workspace_role(workspace_id, current_user, "admin", db)
    await ChatService(db).delete_session(session_id)


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    workspace_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出会话消息"""
    await require_workspace_role(workspace_id, current_user, "viewer", db)
    # 验证会话属于当前用户
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session or str(session.user_id) != str(current_user.id):
        raise ForbiddenException("You can only view your own chat sessions")
    messages = await ChatService(db).list_messages(session_id)
    return [MessageResponse.model_validate(m) for m in messages]


@router.post("/stream")
async def stream_chat(
    workspace_id: str,
    request: ChatStreamRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SSE 流式对话（降级方案 — 主聊天请使用 WebSocket ws/chat）"""
    await require_workspace_role(workspace_id, current_user, "member", db)
    logger.info(f"Chat SSE stream: ws={workspace_id}, session={request.session_id}")

    svc = ChatService(db)
    await svc.save_message(
        session_id=request.session_id, role="user", content=request.message,
    )
    history = await svc.list_messages(request.session_id)

    llm = LLMService()

    async def sse_wrapper():
        try:
            async for event in llm.stream_chat(
                messages=history,
                workspace_id=workspace_id,
                session_id=request.session_id,
            ):
                yield event
        except Exception as e:
            logger.error(f"Stream wrapper error: {e}", exc_info=True)
            yield LLMService._sse("error", {"content": str(e)})

    return StreamingResponse(
        sse_wrapper(),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/send")
async def send_message(
    workspace_id: str,
    request: ChatStreamRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """非流式对话 — HTTP 降级（通过 AgentOrchestrator 走多 Agent 路由）"""
    await require_workspace_role(workspace_id, current_user, "member", db)
    logger.info(f"Chat send: ws={workspace_id}, session={request.session_id}")

    from app.services.agent_orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator(db=db, workspace_id=workspace_id, user=current_user)
    full = ""
    sources = []
    try:
        async for event_dict in orchestrator.run_stream(
            session_id=request.session_id,
            message=request.message,
        ):
            if event_dict["type"] == "token":
                full += event_dict.get("content", "")
            elif event_dict["type"] == "done":
                full = event_dict.get("content", full)
                sources = event_dict.get("sources", [])
            elif event_dict["type"] == "error":
                raise HTTPException(status_code=500, detail=event_dict.get("content", "Unknown error"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Send message error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    return {"reply": full or "No response generated.", "sources": sources}
