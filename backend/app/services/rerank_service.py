"""Rerank 服务 — 使用 BGE Reranker 对向量召回的候选集进行重排序"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

_reranker = None
_executor = ThreadPoolExecutor(max_workers=1)


def _load_reranker():
    """加载 BGE Reranker 模型"""
    global _reranker
    if _reranker is None:
        try:
            from FlagEmbedding import FlagReranker
            _reranker = FlagReranker("BAAI/bge-reranker-base", use_fp16=True)
            logger.info("BGE Reranker loaded successfully")
        except ImportError:
            logger.warning("FlagEmbedding not installed — rerank disabled")
            _reranker = None
        except Exception as e:
            logger.warning(f"Failed to load reranker: {e}")
            _reranker = None
    return _reranker


def _rerank_sync(query: str, candidates: list[str]) -> list[float]:
    """同步计算 rerank 分数"""
    model = _load_reranker()
    if model is None:
        return [0.0] * len(candidates)

    pairs = [[query, doc] for doc in candidates]
    scores = model.compute_score(pairs, normalize=True)

    # 确保返回列表
    if isinstance(scores, float):
        scores = [scores]
    return list(scores)


async def rerank(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    """对候选集进行重排序

    Args:
        query: 查询文本
        candidates: 候选列表，每项包含 content 和元数据
        top_k: 返回结果数

    Returns:
        重排序后的结果列表（分数从高到低）
    """
    if not candidates:
        return []

    if _reranker is None:
        # 未加载 reranker 时跳过重排序
        return candidates[:top_k]

    try:
        # 提取候选文本
        texts = [c.get("content", "") for c in candidates]

        # 在线程池中运行同步 rerank
        loop = asyncio.get_running_loop()
        scores = await loop.run_in_executor(_executor, _rerank_sync, query, texts)

        # 将分数附加到候选项
        for i, c in enumerate(candidates):
            c["rerank_score"] = scores[i] if i < len(scores) else 0.0

        # 按 rerank 分数降序排列
        candidates.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        return candidates[:top_k]

    except Exception as e:
        logger.warning(f"Rerank failed, falling back to original order: {e}")
        return candidates[:top_k]
