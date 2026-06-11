"""文档管理 API — 上传 / 列表 / 删除 + 知识连接器"""

import logging
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_workspace_role
from app.models.user import User
from app.schemas.document import DocumentResponse, DocumentListResponse, UploadResponse
from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workspaces/{workspace_id}/documents", tags=["Documents"])


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出 Workspace 下所有文档（需要 viewer 以上权限）"""
    await require_workspace_role(workspace_id, current_user, "viewer", db)
    documents = await DocumentService(db).list_by_workspace(workspace_id)
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in documents],
        total=len(documents),
    )


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_document(
    workspace_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传文档并触发解析流水线（需要 member 以上权限）"""
    await require_workspace_role(workspace_id, current_user, "member", db)
    return await DocumentService(db).upload(workspace_id, file)


@router.get("/{document_id}/preview")
async def preview_document(
    workspace_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """预览文档内容（返回所有 chunks 拼接后的文本）"""
    await require_workspace_role(workspace_id, current_user, "member", db)
    from sqlalchemy import select
    from app.models.document_chunk import DocumentChunk
    from app.models.document import Document

    # Get document
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id, Document.workspace_id == workspace_id)
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        return {"error": "Document not found"}

    # Get chunks ordered by index
    chunks_result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = chunks_result.scalars().all()

    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "file_type": doc.file_type,
        "source_type": doc.source_type,
        "status": doc.status.value if hasattr(doc.status, 'value') else str(doc.status),
        "chunk_count": len(chunks),
        "content": "\n\n---\n\n".join(c.content for c in chunks) if chunks else "(No content)",
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    workspace_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除文档及其所有 Chunks（需要 admin 权限）"""
    await require_workspace_role(workspace_id, current_user, "admin", db)
    await DocumentService(db).delete(document_id)
