"""报告 API — 生成/列出/下载"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.api.deps import get_current_user, require_workspace_role
from app.models.user import User
from app.models.report import Report
from app.schemas.report import ReportCreate, ReportResponse, ReportListResponse
from app.services.rag_service import RagService
from app.agents.writer_agent import run_writer_agent
from app.services.export_service import export_pdf, export_docx, export_markdown

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces/{workspace_id}/reports", tags=["Reports"])


@router.post("", response_model=ReportResponse, status_code=201)
async def create_report(
    workspace_id: str,
    request: ReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生成报告 — AI Writer Agent 合成"""
    await require_workspace_role(workspace_id, current_user, "member", db)

    # 1. 获取上下文
    context = ""
    if request.query:
        try:
            context = await RagService(db).get_context_for_llm(
                query=request.query,
                workspace_id=workspace_id,
                top_k=5,
            )
        except Exception as e:
            logger.warning(f"RAG context failed: {e}")

    # 2. Writer Agent 生成报告
    result = await run_writer_agent(
        title=request.title,
        context=context or request.content or "No additional context available.",
        user_query=request.query or request.title,
        report_type=request.report_type,
    )

    content = result.get("final_response", request.content or "")

    # 3. 导出文件
    file_path = None
    try:
        import uuid
        safe_name = f"report_{uuid.uuid4().hex[:8]}"
        if request.format == "pdf":
            file_path = export_pdf(content, safe_name)
        elif request.format == "docx":
            file_path = export_docx(content, safe_name)
        else:
            file_path = export_markdown(content, safe_name)
    except Exception as e:
        logger.error(f"Export failed: {e}")

    # 4. 保存到数据库
    report = Report(
        workspace_id=workspace_id,
        title=request.title,
        content=content,
        format=request.format,
        file_path=file_path,
    )
    db.add(report)
    await db.flush()

    return ReportResponse.model_validate(report)


@router.get("", response_model=ReportListResponse)
async def list_reports(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出工作区的报告"""
    await require_workspace_role(workspace_id, current_user, "viewer", db)

    result = await db.execute(
        select(Report)
        .where(Report.workspace_id == workspace_id)
        .order_by(Report.created_at.desc())
    )
    reports = result.scalars().all()

    return ReportListResponse(
        reports=[ReportResponse.model_validate(r) for r in reports],
        total=len(reports),
    )


@router.delete("/{report_id}", status_code=204)
async def delete_report(
    workspace_id: str,
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a report (admin only)"""
    await require_workspace_role(workspace_id, current_user, "admin", db)
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.workspace_id == workspace_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    # Delete file if exists
    if report.file_path:
        from pathlib import Path
        Path(report.file_path).unlink(missing_ok=True)
    await db.delete(report)


@router.get("/{report_id}/download")
async def download_report(
    workspace_id: str,
    report_id: str,
    format: str = "",
    token: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Download report file (PDF/DOCX/Markdown). Use ?format=pdf or ?format=docx to convert.

    Auth via ?token= query param (for browser link clicks) or Authorization header.
    """
    # Auth: query param token or header
    from app.api.deps import get_current_user
    from fastapi import Header
    from app.core.security import decode_access_token
    from jose import JWTError

    if token:
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
            result = await db.execute(select(User).where(User.id == user_id))
            current_user = result.scalar_one_or_none()
            if not current_user or not current_user.is_active:
                raise HTTPException(status_code=401, detail="Invalid token")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    else:
        # Fall back to header auth
        raise HTTPException(status_code=401, detail="Authentication required. Use ?token= query parameter.")

    await require_workspace_role(workspace_id, current_user, "viewer", db)

    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.workspace_id == workspace_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    from pathlib import Path
    from app.services.export_service import export_pdf, export_docx, export_markdown
    import uuid as uuid_mod

    output_format = format or report.format
    content = report.content

    # Generate file on-the-fly if not cached
    safe_name = f"report_{uuid_mod.uuid4().hex[:8]}"
    try:
        if output_format == "pdf":
            file_path = export_pdf(content, safe_name)
            media_type = "application/pdf"
            ext = "pdf"
        elif output_format == "docx":
            file_path = export_docx(content, safe_name)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ext = "docx"
        else:
            file_path = report.file_path or export_markdown(content, safe_name)
            media_type = "text/markdown"
            ext = "md"
    except Exception as e:
        logger.error(f"Export failed for report {report_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

    # Cache the generated file for future downloads
    if not report.file_path:
        report.file_path = file_path
        await db.flush()

    out_path = Path(file_path) if Path(file_path).exists() else Path(file_path)
    return FileResponse(
        path=str(out_path),
        media_type=media_type,
        filename=f"{report.title[:50]}.{ext}",
    )
