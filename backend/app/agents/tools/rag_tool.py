"""RAG 工具 — LangChain @tool 装饰的向量搜索函数"""

import logging
from typing import Optional

from langchain_core.tools import tool

from app.database import AsyncSessionLocal
from app.services.rag_service import RagService

logger = logging.getLogger(__name__)


@tool
async def search_knowledge_base(
    query: str,
    workspace_id: str,
    top_k: int = 5,
) -> str:
    """在知识库中搜索与查询相关的文档内容。

    Args:
        query: 搜索查询文本
        workspace_id: 工作区 ID
        top_k: 返回结果数，默认 5

    Returns:
        格式化的搜索结果文本，包含来源信息
    """
    try:
        async with AsyncSessionLocal() as session:
            results = await RagService(session).search(
                query=query,
                workspace_id=workspace_id,
                top_k=top_k,
            )
        if not results:
            return "No relevant documents found in the knowledge base."

        parts = []
        for i, r in enumerate(results):
            parts.append(
                f"[Source {i+1}: {r.filename} (similarity: {r.similarity:.0%})]\n{r.content}"
            )
        return "\n\n---\n\n".join(parts)
    except Exception as e:
        logger.error(f"Knowledge base search failed: {e}")
        return f"Search error: {str(e)}"
