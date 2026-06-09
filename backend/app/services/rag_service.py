"""RAG 检索服务 — pgvector 向量相似搜索 + Hybrid + Rerank (ORM)"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func

from app.models.document_chunk import DocumentChunk
from app.models.document import Document
from app.services.embedding_service import embed_single
from app.services.rerank_service import rerank
from app.services.query_rewrite_service import rewrite_query
from app.schemas.search import SearchResultItem

logger = logging.getLogger(__name__)

# 混合搜索权重
HYBRID_WEIGHT_VECTOR = 0.7
HYBRID_WEIGHT_KEYWORD = 0.3


class RagService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(
        self,
        query: str,
        workspace_id: str,
        top_k: int = 5,
        rewrite: bool = True,
        filters: Optional[dict] = None,
    ) -> list[SearchResultItem]:
        """增强语义搜索：Query Rewrite → 向量/关键词召回 → Rerank

        Args:
            query: 用户查询
            workspace_id: 工作区 ID
            top_k: 返回结果数
            rewrite: 是否启用 LLM 查询重写
            filters: 元数据过滤器 {"file_type": "pdf", "filename_contains": "report"}
        """
        # 1. Query Rewrite（可选）
        search_query = query
        if rewrite and len(query) > 5:
            try:
                search_query = await rewrite_query(query)
            except Exception as e:
                logger.warning(f"Query rewrite skipped: {e}")

        # 2. 向量召回（Top-20 给 Rerank）
        recall_k = max(top_k * 4, 20)
        query_emb = await embed_single(search_query)

        doc_ids = select(Document.id).where(Document.workspace_id == workspace_id).scalar_subquery()
        dist_expr = DocumentChunk.embedding.cosine_distance(query_emb).label("distance")
        sim_expr = (1.0 - DocumentChunk.embedding.cosine_distance(query_emb)).label("similarity")

        stmt = (
            select(DocumentChunk, Document.filename, Document.file_type, dist_expr, sim_expr)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.document_id.in_(doc_ids))
            .where(DocumentChunk.embedding.isnot(None))
            .order_by(dist_expr)
            .limit(recall_k)
        )

        # Metadata Filter
        if filters:
            if "file_type" in filters:
                stmt = stmt.where(Document.file_type == filters["file_type"])
            if "filename_contains" in filters:
                stmt = stmt.where(Document.filename.ilike(f"%{filters['filename_contains']}%"))

        result = await self.db.execute(stmt)
        rows = result.all()

        # 3. 构建候选集
        candidates = []
        for chunk, filename, file_type, distance, similarity in rows:
            dist_val = float(distance) if distance is not None else 1.0
            sim_val = float(similarity) if similarity is not None else 1.0 - dist_val

            if sim_val <= 0.0:
                continue

            candidates.append({
                "chunk": chunk,
                "filename": filename,
                "file_type": file_type,
                "distance": dist_val,
                "similarity": sim_val,
                "content": chunk.content,
            })

        # 4. Rerank（如果候选集 > top_k）
        if len(candidates) > top_k:
            try:
                candidates = await rerank(
                    query=query,  # 使用原始查询进行 rerank
                    candidates=candidates,
                    top_k=top_k,
                )
            except Exception as e:
                logger.warning(f"Rerank skipped: {e}")
                candidates = candidates[:top_k]
        else:
            candidates = candidates[:top_k]

        # 5. 构建结果
        items = []
        for c in candidates:
            chunk = c["chunk"]
            sim = c.get("rerank_score", c.get("similarity", 0))
            items.append(SearchResultItem(
                chunk_id=str(chunk.id),
                document_id=str(chunk.document_id),
                filename=c["filename"],
                content=chunk.content,
                metadata=chunk.metadata_,
                similarity=round(sim, 4),
            ))

        return items

    async def get_context_for_llm(
        self,
        query: str,
        workspace_id: str,
        top_k: int = 5,
    ) -> str:
        results = await self.search(query, workspace_id, top_k)
        if not results:
            return ""
        parts = []
        for i, r in enumerate(results):
            parts.append(f"[Source {i+1}: {r.filename}]\n{r.content}")
        return "\n\n---\n\n".join(parts)


# ---- LangChain Retriever 适配器 ----


from typing import List
from langchain_core.documents import Document as LCDocument
from langchain_core.retrievers import BaseRetriever
from pydantic import Field


class PgVectorRetriever(BaseRetriever):
    """LangChain BaseRetriever 适配器 — 将 RagService 包装为标准 Retriever 接口"""

    rag_service: RagService = Field(...)
    workspace_id: str = Field(...)
    top_k: int = Field(default=5)

    class Config:
        arbitrary_types_allowed = True

    async def _aget_relevant_documents(self, query: str) -> List[LCDocument]:
        results = await self.rag_service.search(
            query=query,
            workspace_id=self.workspace_id,
            top_k=self.top_k,
        )
        docs = []
        for r in results:
            docs.append(LCDocument(
                page_content=r.content,
                metadata={
                    "document_id": r.document_id,
                    "chunk_id": r.chunk_id,
                    "filename": r.filename,
                    "similarity": r.similarity,
                    **(r.metadata or {}),
                },
            ))
        return docs

    def _get_relevant_documents(self, query: str) -> List[LCDocument]:
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self._aget_relevant_documents(query))
