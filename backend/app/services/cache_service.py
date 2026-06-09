"""Redis 缓存服务"""

import json
import logging
from typing import Optional, Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class CacheService:
    """Redis 缓存封装

    用途：
    - 会话消息缓存（TTL 5 分钟）
    - 搜索结果缓存（TTL 10 分钟）
    - 速率限制计数器
    """

    def __init__(self, redis: Optional[Redis] = None):
        self._redis = redis

    @property
    def available(self) -> bool:
        return self._redis is not None

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self._redis:
            return None
        try:
            val = await self._redis.get(key)
            if val:
                return json.loads(val)
            return None
        except Exception as e:
            logger.warning(f"Cache get failed for {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """设置缓存值"""
        if not self._redis:
            return False
        try:
            await self._redis.set(key, json.dumps(value), ex=ttl)
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        if not self._redis:
            return False
        try:
            await self._redis.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed for {key}: {e}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """按模式失效缓存"""
        if not self._redis:
            return 0
        try:
            keys = await self._redis.keys(pattern)
            if keys:
                return await self._redis.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache invalidate failed for {pattern}: {e}")
            return 0

    # ---- 语义化方法 ----

    async def cache_chat_session(self, session_id: str, messages: list[dict]) -> bool:
        """缓存会话消息（TTL 5 分钟）"""
        return await self.set(f"chat:session:{session_id}", messages, ttl=300)

    async def get_chat_session(self, session_id: str) -> Optional[list[dict]]:
        """获取缓存的会话消息"""
        return await self.get(f"chat:session:{session_id}")

    async def invalidate_chat_session(self, session_id: str):
        """新消息时失效会话缓存"""
        await self.delete(f"chat:session:{session_id}")

    async def cache_search_result(self, query: str, workspace_id: str, results: list[dict]) -> bool:
        """缓存搜索结果（TTL 10 分钟）"""
        key = f"search:{workspace_id}:{hash(query)}"
        return await self.set(key, results, ttl=600)

    async def get_search_result(self, query: str, workspace_id: str) -> Optional[list[dict]]:
        """获取缓存的搜索结果"""
        key = f"search:{workspace_id}:{hash(query)}"
        return await self.get(key)
