"""文档读取工具 — 按 ID 读取文档完整内容"""

import logging

from langchain_core.tools import tool
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.document import Document

logger = logging.getLogger(__name__)


@tool
async def read_document(document_id: str) -> str:
    """读取指定文档的完整内容。

    当需要深入了解某个特定文档的全部内容时使用。

    Args:
        document_id: 文档的 UUID

    Returns:
        文档的完整文本内容
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = result.scalar_one_or_none()

            if not doc:
                return f"Document not found: {document_id}"

            # 读取文件内容
            filepath = doc.file_path
            if not filepath:
                return f"Document has no file path: {doc.filename}"

            from pathlib import Path
            fp = Path(filepath)
            if not fp.exists():
                return f"Document file not found on disk: {doc.filename}"

            from app.services.document_service import PARSERS
            ext = fp.suffix.lower()
            parser = PARSERS.get(ext)
            if not parser:
                return f"No parser available for file type: {ext}"

            text = parser(str(fp))
            return f"## {doc.filename}\n\n{text[:10000]}"  # 限制 10000 字符

    except Exception as e:
        logger.error(f"Document read failed: {e}")
        return f"Read error: {str(e)}"
