"""WebSocket 聊天端点"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from app.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.services.ws_manager import ws_manager
from app.services.agent_orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


async def get_user_from_token(token: str, db: AsyncSession) -> User | None:
    """从 query param token 中验证并返回用户"""
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
    except JWTError:
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None
    return user


@router.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    token: str = Query(...),
    session_id: str = Query(...),
    workspace_id: str = Query(...),
):
    """WebSocket 流式聊天端点

    Query 参数：
    - token: JWT access token
    - session_id: 聊天会话 ID
    - workspace_id: 工作区 ID
    """
    # 1. 数据库会话
    from app.database import AsyncSessionLocal

    db = AsyncSessionLocal()
    conn_id = None

    try:
        # 2. 认证
        user = await get_user_from_token(token, db)
        if not user:
            logger.warning(f"WS auth failed: invalid token")
            await websocket.close(code=4001, reason="Unauthorized")
            return

        # 3. 接受连接
        await websocket.accept()
        conn_id = await ws_manager.connect(
            websocket,
            user_id=str(user.id),
            workspace_id=workspace_id,
            session_id=session_id,
        )

        await websocket.send_json({
            "type": "connected",
            "data": {
                "session_id": session_id,
                "workspace_id": workspace_id,
            },
        })

        logger.info(f"WS chat started: user={user.id} session={session_id}")

        # 4. 消息循环
        while True:
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                logger.info(f"WS client disconnected: {conn_id}")
                break

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "data": {"content": "Invalid JSON", "code": "PARSE_ERROR"},
                })
                continue

            msg_type = msg.get("type", "")

            if msg_type == "ping":
                # 心跳响应
                await websocket.send_json({"type": "pong"})

            elif msg_type == "message":
                # 聊天消息
                content = msg.get("data", {}).get("content", "")
                if not content.strip():
                    await websocket.send_json({
                        "type": "error",
                        "data": {"content": "Empty message", "code": "EMPTY_MESSAGE"},
                    })
                    continue

                # 运行 AgentOrchestrator
                orchestrator = AgentOrchestrator(
                    db=db,
                    workspace_id=workspace_id,
                    user=user,
                )
                async for event in orchestrator.run_stream(
                    session_id=session_id,
                    message=content,
                ):
                    await websocket.send_json(event)

            elif msg_type == "cancel":
                # 取消当前生成（TODO: 接入 LangGraph interrupt）
                await websocket.send_json({
                    "type": "status",
                    "data": {"content": "Generation cancelled"},
                })

            else:
                await websocket.send_json({
                    "type": "error",
                    "data": {"content": f"Unknown message type: {msg_type}", "code": "UNKNOWN_TYPE"},
                })

    except WebSocketDisconnect:
        logger.info(f"WS disconnected: {conn_id}")
    except Exception as e:
        logger.error(f"WS error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "data": {"content": f"Internal error: {str(e)}", "code": "INTERNAL"},
            })
        except Exception:
            pass
    finally:
        if conn_id:
            await ws_manager.disconnect(conn_id)
        await db.close()
