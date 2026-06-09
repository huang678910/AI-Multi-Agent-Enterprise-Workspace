"""WebSocket 连接管理器 — 内存 + Redis 注册表"""

import asyncio
import json
import logging
import uuid
from typing import Optional

from fastapi import WebSocket
from redis.asyncio import Redis

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class WebSocketManager:
    """管理所有活跃的 WebSocket 连接

    特性：
    - 内存注册表（快速查找）
    - Redis 注册表（多实例支持）
    - 心跳检测（清理死连接）
    - 按 session 广播
    """

    def __init__(self):
        self._connections: dict[str, WebSocket] = {}  # conn_id → WebSocket
        self._metadata: dict[str, dict] = {}           # conn_id → {user_id, session_id, workspace_id}
        self._redis: Optional[Redis] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def initialize(self, redis: Optional[Redis] = None):
        """初始化 Redis 连接并启动心跳"""
        self._redis = redis
        if self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info("WebSocket heartbeat loop started")

    async def shutdown(self):
        """关闭所有连接并停止心跳"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        for conn_id in list(self._connections.keys()):
            await self.disconnect(conn_id)
        logger.info("WebSocket manager shut down")

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        workspace_id: str,
        session_id: str,
    ) -> str:
        """注册新连接，返回 connection_id"""
        conn_id = str(uuid.uuid4())
        self._connections[conn_id] = websocket
        self._metadata[conn_id] = {
            "user_id": user_id,
            "workspace_id": workspace_id,
            "session_id": session_id,
        }

        # Redis 注册（用于多实例）
        if self._redis:
            try:
                await self._redis.hset(
                    f"ws:session:{session_id}",
                    conn_id,
                    json.dumps({
                        "user_id": user_id,
                        "workspace_id": workspace_id,
                    }),
                )
                await self._redis.expire(f"ws:session:{session_id}", 3600)
            except Exception as e:
                logger.warning(f"Redis WS registration failed: {e}")

        logger.info(f"WS connected: {conn_id} user={user_id} session={session_id}")
        return conn_id

    async def disconnect(self, conn_id: str):
        """移除连接"""
        ws = self._connections.pop(conn_id, None)
        meta = self._metadata.pop(conn_id, {})

        if ws:
            try:
                await ws.close()
            except Exception:
                pass

        # 从 Redis 移除
        session_id = meta.get("session_id", "")
        if self._redis and session_id:
            try:
                await self._redis.hdel(f"ws:session:{session_id}", conn_id)
            except Exception:
                pass

        logger.info(f"WS disconnected: {conn_id}")

    async def send_event(self, conn_id: str, event: dict):
        """向指定连接发送 JSON 事件"""
        ws = self._connections.get(conn_id)
        if ws:
            try:
                await ws.send_json(event)
            except Exception as e:
                logger.warning(f"Failed to send to {conn_id}: {e}")
                await self.disconnect(conn_id)

    async def _heartbeat_loop(self):
        """定期检测死连接"""
        while True:
            await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
            dead = []
            for conn_id, ws in list(self._connections.items()):
                try:
                    await ws.send_json({"type": "ping"})
                except Exception:
                    dead.append(conn_id)
            for conn_id in dead:
                logger.info(f"WS heartbeat dead: {conn_id}")
                await self.disconnect(conn_id)


# 全局单例
ws_manager = WebSocketManager()
