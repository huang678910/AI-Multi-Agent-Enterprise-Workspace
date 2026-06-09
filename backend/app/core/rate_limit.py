"""Redis 滑动窗口速率限制器"""

import time
import logging
from typing import Optional

from fastapi import Request, HTTPException
from redis.asyncio import Redis

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimiter:
    """基于 Redis 的滑动窗口速率限制"""

    def __init__(self, redis: Optional[Redis] = None):
        self._redis = redis

    async def check(
        self,
        key: str,
        max_requests: int = 30,
        window_seconds: int = 60,
    ) -> bool:
        """检查是否超过速率限制

        Args:
            key: 限制键（如 user_id 或 IP）
            max_requests: 时间窗口内最大请求数
            window_seconds: 时间窗口（秒）

        Returns:
            True 如果允许，False 如果超限
        """
        if not self._redis:
            return True  # 没有 Redis 时跳过限制

        now = time.time()
        window_start = now - window_seconds
        redis_key = f"rate_limit:{key}"

        try:
            async with self._redis.pipeline() as pipe:
                # 移除窗口外的记录
                await pipe.zremrangebyscore(redis_key, 0, window_start)
                # 统计窗口内记录数
                await pipe.zcard(redis_key)
                # 添加当前请求
                await pipe.zadd(redis_key, {str(now): now})
                # 设置过期
                await pipe.expire(redis_key, window_seconds + 1)
                results = await pipe.execute()

            current_count = results[1]  # zcard 的结果
            return current_count < max_requests
        except Exception as e:
            logger.warning(f"Rate limit check failed: {e}")
            return True  # Redis 异常时放行


# 全局单例
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


async def create_rate_limit_middleware(app):
    """在 FastAPI app 上注册速率限制中间件"""
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    class RateLimitMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            # 只限制 API 端点
            if not request.url.path.startswith("/api/"):
                return await call_next(request)

            limiter = get_rate_limiter()
            # 使用用户 ID 或 IP 作为键
            key = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
            allowed = await limiter.check(
                key=key,
                max_requests=settings.RATE_LIMIT_PER_MINUTE,
                window_seconds=60,
            )
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Try again later."},
                )
            return await call_next(request)

    app.add_middleware(RateLimitMiddleware)
