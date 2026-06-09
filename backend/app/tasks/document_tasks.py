"""Async document processing tasks"""

import logging
from app.celery_app import celery
from app.database import AsyncSessionLocal
from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=3, default_retry_delay=30)
def process_document_async(self, doc_id: str):
    """Process uploaded document asynchronously: parse -> chunk -> embed -> store"""
    import asyncio

    async def _process():
        async with AsyncSessionLocal() as db:
            svc = DocumentService(db)
            doc = await svc.get_by_id(doc_id)
            if not doc:
                raise ValueError(f"Document {doc_id} not found")

            try:
                await svc._process_document(doc)
                await db.commit()
                return {"status": "ready", "chunk_count": doc.chunk_count}
            except Exception as e:
                doc.status = "error"
                doc.error_message = str(e)
                await db.commit()
                raise

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
        result = asyncio.run(_process())
        return result
    except Exception as exc:
        logger.error(f"Document processing failed for {doc_id}: {exc}")
        raise self.retry(exc=exc)
