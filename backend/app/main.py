"""AI Multi-Agent Enterprise Workspace — FastAPI 应用入口"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.api.v1.router import api_router

logger = logging.getLogger(__name__)
settings = get_settings()


async def _bg_warmup():
    try:
        from app.services.embedding_service import warmup_embedding_model
        await warmup_embedding_model()
        logger.info("Embedding model warmed up")
    except Exception as e:
        logger.warning(f"Embedding model warmup failed (will retry on first request): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时加载模型 + 连接 Redis + 启动 WS 管理，关闭时清理资源"""
    # 启动时：后台预热 Embedding 模型（不阻塞启动，120s 超时）
    import asyncio as _asyncio
    _asyncio.ensure_future(_asyncio.wait_for(_bg_warmup(), timeout=120))
    logger.info("Embedding model warmup started in background")

    # 启动时：连接 Redis
    redis_client = None
    try:
        import redis.asyncio as aioredis
        redis_client = aioredis.from_url(
            settings.redis_url, encoding="utf-8", decode_responses=True
        )
        await redis_client.ping()
        app.state.redis = redis_client
        logger.info("Redis connected: %s", settings.redis_url)
    except Exception:
        logger.warning("Redis unavailable at %s — caching disabled", settings.redis_url)
        app.state.redis = None

    # 启动时：初始化 WebSocket 管理器
    try:
        from app.services.ws_manager import ws_manager
        await ws_manager.initialize(redis_client)
        app.state.ws_manager = ws_manager
        logger.info("WebSocket manager initialized")
    except Exception:
        logger.warning("WebSocket manager initialization failed")

    # 启动时：注册速率限制器
    try:
        from app.core.rate_limit import get_rate_limiter, RateLimiter
        limiter = RateLimiter(redis_client)
        app.state.rate_limiter = limiter
        logger.info("Rate limiter initialized")
    except Exception:
        logger.warning("Rate limiter initialization failed")

    # 启动时：注册所有工具到 Tool Registry
    try:
        from app.agents.tools.tool_registry import get_tool_registry
        registry = get_tool_registry()
        from app.agents.tools.rag_tool import search_knowledge_base
        from app.agents.tools.web_search_tool import search_web
        from app.agents.tools.document_reader_tool import read_document
        from app.agents.tools.python_executor_tool import execute_python
        from app.agents.tools.sql_tool import query_database
        from app.agents.tools.report_generator_tool import generate_report
        from app.agents.tools.memory_tool import save_memory, recall_memory
        from app.agents.tools.graph_tool import query_graph, search_graph
        for t in [search_knowledge_base, search_web, read_document, execute_python, query_database, generate_report, save_memory, recall_memory, query_graph, search_graph]:
            registry.register(t)
        logger.info(f"Tool registry initialized: {registry.count()} tools")
    except Exception:
        logger.warning("Tool registry initialization failed")

    yield

    # 关闭时：清理
    try:
        if hasattr(app.state, "ws_manager"):
            await app.state.ws_manager.shutdown()
    except Exception:
        pass

    if app.state.redis:
        await app.state.redis.close()
        logger.info("Redis disconnected")


app = FastAPI(
    title=settings.APP_NAME,
    version="0.2.0",
    description="Enterprise AI Knowledge Work Platform with Multi-Agent Collaboration",
    lifespan=lifespan,
)

# CORS — MVP 允许所有来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理 — 不覆盖 HTTPException 的状态码"""
    from fastapi.exceptions import HTTPException
    if isinstance(exc, HTTPException):
        from starlette.responses import Response
        # 让 FastAPI 内置的 HTTPException handler 处理
        raise exc
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )


# 挂载路由
app.include_router(api_router)


@app.get("/", tags=["Health"])
async def root():
    return {"name": settings.APP_NAME, "version": "0.2.0", "status": "running"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "database": "pending", "embedding_model": settings.EMBEDDING_MODEL}
