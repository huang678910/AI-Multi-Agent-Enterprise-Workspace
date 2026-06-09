"""知识中心 API — 外部连接器 + 音频转录"""

import uuid
import logging
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_workspace_role
from app.models.user import User
from app.services.document_service import DocumentService
from app.services.connectors.github_connector import GitHubConnector

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workspaces/{workspace_id}/knowledge", tags=["Knowledge Hub"])


async def _check_member(workspace_id: str, current_user: User, db: AsyncSession):
    await require_workspace_role(workspace_id, current_user, "member", db)


# ─── GitHub Connector ─────────────────────────────────

@router.post("/connect/github")
async def connect_github(
    workspace_id: uuid.UUID,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Connect a GitHub repository and sync its README + Issues into the knowledge base"""
    await _check_member(str(workspace_id), current_user, db)

    token = body.get("token", "")
    owner = body.get("owner", "")
    repo = body.get("repo", "")

    if not all([token, owner, repo]):
        return {"error": "token, owner, and repo are required"}

    connector = GitHubConnector({"token": token, "owner": owner, "repo": repo})

    # Validate connection
    if not await connector.validate_connection():
        return {"error": f"Failed to connect to github.com/{owner}/{repo}. Check your token and repo name."}

    # Fetch data
    items = await connector.fetch_all()
    if not items:
        return {"status": "ok", "synced": 0, "message": "No content found to sync."}

    # Ingest into knowledge base
    doc_svc = DocumentService(db)
    synced = 0
    for item in items:
        try:
            doc = await doc_svc.create_document(
                workspace_id=str(workspace_id),
                filename=f"github:{owner}/{repo}:{item.title[:100]}",
                file_type="markdown",
                file_size=len(item.content.encode("utf-8")),
                source_type="github",
            )
            # Trigger chunk processing (simple: single chunk for connector content)
            from app.models.document_chunk import DocumentChunk
            from app.services.embedding_service import embed_texts
            chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=0,
                content=item.content,
                source_type="github",
                content_type="text",
                metadata_=item.metadata or {},
            )
            # Generate embedding so RAG can find it
            try:
                embeddings = await embed_texts([item.content[:2000]])
                if embeddings and embeddings[0]:
                    chunk.embedding = embeddings[0]
            except Exception as emb_err:
                logger.warning(f"Embedding generation failed for GitHub item: {emb_err}")
            db.add(chunk)
            synced += 1
        except Exception as e:
            logger.warning(f"Failed to ingest GitHub item {item.title}: {e}")
            continue

    await db.flush()
    return {"status": "ok", "synced": synced, "message": f"Synced {synced} items from {owner}/{repo}"}


@router.get("/connections")
async def list_connections(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List active external knowledge connections"""
    await _check_member(str(workspace_id), current_user, db)

    # Check for documents with non-upload source_type
    from sqlalchemy import select
    from app.models.document import Document
    result = await db.execute(
        select(Document).where(
            Document.workspace_id == workspace_id,
            Document.source_type != "upload",
        )
    )
    docs = result.scalars().all()

    connections = {}
    for doc in docs:
        key = doc.source_type
        if key not in connections:
            connections[key] = {"source_type": key, "doc_count": 0, "last_synced": None}
        connections[key]["doc_count"] += 1
        if not connections[key]["last_synced"] or doc.created_at > connections[key]["last_synced"]:
            connections[key]["last_synced"] = doc.created_at.isoformat()

    return {"connections": list(connections.values())}


# ─── Audio Transcription ──────────────────────────────

@router.post("/transcribe")
async def transcribe_audio(
    workspace_id: uuid.UUID,
    file: UploadFile = File(...),
    language: str = Form("zh"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload an audio file and transcribe it to text, then add to knowledge base"""
    await _check_member(str(workspace_id), current_user, db)

    # Validate file type
    allowed = {"audio/mpeg", "audio/wav", "audio/mp4", "audio/ogg", "audio/x-m4a",
               "audio/mp3", "audio/wave", "audio/webm"}
    if file.content_type and file.content_type not in allowed:
        # Also check by extension
        ext = (file.filename or "").rsplit(".", 1)[-1].lower()
        if ext not in ("mp3", "wav", "m4a", "ogg", "webm", "flac"):
            return {"error": f"Unsupported audio format: {file.content_type or ext}. Supported: mp3, wav, m4a, ogg, webm"}

    # Save temp file
    import tempfile
    import os
    suffix = "." + (file.filename or "audio").rsplit(".", 1)[-1] if file.filename and "." in file.filename else ".mp3"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    if len(content) > 25 * 1024 * 1024:
        os.unlink(tmp_path)
        return {"error": "Audio file exceeds 25MB limit"}

    try:
        from app.services.whisper_service import transcribe_audio as whisper_transcribe
        text = await whisper_transcribe(tmp_path, language=language)
    finally:
        os.unlink(tmp_path)  # Clean up temp file

    if not text or text.startswith("["):
        return {"error": text or "Transcription produced no text"}

    # Save as document in knowledge base
    doc_svc = DocumentService(db)
    doc = await doc_svc.create_document(
        workspace_id=str(workspace_id),
        filename=file.filename or "recording.mp3",
        file_type="audio",
        file_size=len(text.encode("utf-8")),
        source_type="upload",
    )

    from app.models.document_chunk import DocumentChunk
    from app.services.embedding_service import embed_texts
    # Include filename in content so RAG can find it by name
    indexed_content = f"[Audio File: {file.filename}]\n\n{text}"
    chunk = DocumentChunk(
        document_id=doc.id,
        chunk_index=0,
        content=indexed_content,
        source_type="upload",
        content_type="audio_transcript",
    )
    # Generate embedding so RAG can find it
    try:
        embeddings = await embed_texts([indexed_content[:2000]])
        if embeddings and embeddings[0]:
            chunk.embedding = embeddings[0]
    except Exception as emb_err:
        logger.warning(f"Embedding generation failed for audio transcript: {emb_err}")
    db.add(chunk)
    await db.flush()

    return {
        "status": "ok",
        "document_id": str(doc.id),
        "filename": file.filename,
        "transcript": text[:500] + ("..." if len(text) > 500 else ""),
        "full_length": len(text),
    }
