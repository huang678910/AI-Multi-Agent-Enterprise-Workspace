"""Embedding 服务 — 基于 sentence-transformers 的本地向量化"""

import os
# 仅在 Docker/生产环境开启离线模式（模型预装于 Dockerfile）
# 本地开发：若未设置 HF_HUB_OFFLINE，允许从 HuggingFace 下载
if os.environ.get("HF_HUB_OFFLINE") is None and os.environ.get("DOCKER_ENV") is None:
    # 本地开发：使用国内镜像加速
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
# Docker：保持离线模式
if os.environ.get("DOCKER_ENV"):
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 全局单例
_embed_model = None
_executor = ThreadPoolExecutor(max_workers=2)


def _load_model():
    """在后台线程中加载模型（避免阻塞事件循环）"""
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer

        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        _embed_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info("Embedding model loaded successfully")


async def warmup_embedding_model():
    """FastAPI 启动时预热：加载模型到内存"""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(_executor, _load_model)


def _encode_sync(texts: list[str]) -> list[list[float]]:
    """同步编码文本（运行在线程池中）"""
    if _embed_model is None:
        _load_model()
    embeddings = _embed_model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return embeddings.tolist()


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """异步批量编码文本"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _encode_sync, texts)


async def embed_single(text: str) -> list[float]:
    """异步编码单个文本"""
    results = await embed_texts([text])
    return results[0]


# ---- LangChain Embeddings 适配器 ----


_langchain_embeddings = None


def get_langchain_embeddings():
    """获取 LangChain HuggingFaceEmbeddings 实例（可选，用于 LangChain chain）"""
    global _langchain_embeddings
    if _langchain_embeddings is None:
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            _langchain_embeddings = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            logger.info("LangChain HuggingFaceEmbeddings initialized")
        except ImportError:
            logger.warning(
                "langchain-huggingface not installed — "
                "get_langchain_embeddings() will return None"
            )
            return None
    return _langchain_embeddings
