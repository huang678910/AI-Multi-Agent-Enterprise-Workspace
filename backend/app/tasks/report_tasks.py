"""Async report generation tasks"""

import logging
from app.celery_app import celery
from app.database import AsyncSessionLocal
from app.models.report import Report
from app.services.export_service import export_markdown, export_pdf, export_docx
import uuid as uuid_mod

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=2, default_retry_delay=60)
def generate_report_async(self, workspace_id: str, title: str, content: str, fmt: str = "markdown"):
    """Generate report and export file asynchronously"""
    import asyncio

    async def _generate():
        async with AsyncSessionLocal() as db:
            report = Report(
                workspace_id=workspace_id,
                title=title,
                content=content,
                format=fmt,
            )
            db.add(report)
            await db.flush()

            safe_name = f"report_{uuid_mod.uuid4().hex[:8]}"
            if fmt == "pdf":
                path = export_pdf(content, safe_name)
            elif fmt == "docx":
                path = export_docx(content, safe_name)
            else:
                path = export_markdown(content, safe_name)

            report.file_path = path
            await db.commit()
            return {"report_id": str(report.id), "file_path": path, "format": fmt}

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
        return asyncio.run(_generate())
    except Exception as exc:
        logger.error(f"Report generation failed: {exc}")
        raise self.retry(exc=exc)
