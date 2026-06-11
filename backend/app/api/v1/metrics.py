"""数字孪生 REST API — /api/v1/workspaces/{workspace_id}/metrics/..."""

import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_workspace_role
from app.models.user import User
from app.services.business_metrics_service import BusinessMetricsService
from app.schemas.business_metrics import (
    MetricCreate, MetricBatchCreate, MetricUpdate,
    MetricResponse, MetricListResponse, MetricSnapshot, MetricTrendResponse, MetricTrendPoint, MetricSummaryResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workspaces/{workspace_id}/metrics", tags=["Digital Twin Metrics"])


# ─── Helpers ───────────────────────────────────────────

async def _get_svc(workspace_id: str, current_user: User, min_role: str, db: AsyncSession) -> BusinessMetricsService:
    await require_workspace_role(workspace_id, current_user, min_role, db)
    return BusinessMetricsService(db)


# ─── CRUD ───────────────────────────────────────────────

@router.get("", response_model=MetricListResponse)
async def list_metrics(
    workspace_id: uuid.UUID,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出所有业务指标（按时间倒序，支持分类筛选）"""
    await require_workspace_role(str(workspace_id), current_user, "viewer", db)
    svc = BusinessMetricsService(db)
    metrics = await svc.list_by_workspace(str(workspace_id), category)
    return MetricListResponse(
        metrics=[MetricResponse.model_validate(m) for m in metrics],
        total=len(metrics),
    )


@router.post("/record", response_model=MetricResponse, status_code=201)
async def record_metric(
    workspace_id: uuid.UUID,
    body: MetricCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """记录单个业务指标"""
    await require_workspace_role(str(workspace_id), current_user, "member", db)
    try:
        svc = BusinessMetricsService(db)
        metric = await svc.record(str(workspace_id), body.model_dump())
        await db.commit()
        return MetricResponse.model_validate(metric)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch", response_model=MetricListResponse, status_code=201)
async def batch_record_metrics(
    workspace_id: uuid.UUID,
    body: MetricBatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量记录业务指标"""
    await require_workspace_role(str(workspace_id), current_user, "member", db)
    try:
        svc = BusinessMetricsService(db)
        metrics = await svc.batch_record(str(workspace_id), [m.model_dump() for m in body.metrics])
        await db.commit()
        return MetricListResponse(
            metrics=[MetricResponse.model_validate(m) for m in metrics],
            total=len(metrics),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{metric_id}", response_model=MetricResponse)
async def update_metric(
    workspace_id: uuid.UUID,
    metric_id: uuid.UUID,
    body: MetricUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新指标值或备注"""
    await require_workspace_role(str(workspace_id), current_user, "member", db)
    svc = BusinessMetricsService(db)
    metric = await svc.update(str(metric_id), body.model_dump(exclude_none=True))
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    await db.commit()
    return MetricResponse.model_validate(metric)


@router.delete("/{metric_id}", status_code=204)
async def delete_metric(
    workspace_id: uuid.UUID,
    metric_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除一条指标记录（需要 admin 权限）"""
    await require_workspace_role(str(workspace_id), current_user, "admin", db)
    svc = BusinessMetricsService(db)
    deleted = await svc.delete(str(metric_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Metric not found")
    await db.commit()


# ─── 查询 ───────────────────────────────────────────────

@router.get("/snapshot", response_model=MetricSnapshot)
async def get_snapshot(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取最新指标快照（每个 metric_name 最新值）"""
    await require_workspace_role(str(workspace_id), current_user, "viewer", db)
    svc = BusinessMetricsService(db)
    metrics = await svc.get_snapshot(str(workspace_id))
    return MetricSnapshot(
        company_id=str(workspace_id),
        metrics=[MetricResponse.model_validate(m) for m in metrics],
        generated_at=datetime.utcnow().isoformat(),
    )


@router.get("/trend/{metric_name}", response_model=MetricTrendResponse)
async def get_trend(
    workspace_id: uuid.UUID,
    metric_name: str,
    periods: int = 12,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取某个指标的时间序列趋势"""
    await require_workspace_role(str(workspace_id), current_user, "viewer", db)
    svc = BusinessMetricsService(db)
    data_points = await svc.get_trend(str(workspace_id), metric_name, periods)

    # Calculate change and direction
    change_pct = None
    trend_direction = "flat"
    if len(data_points) >= 2:
        first_val = data_points[0]["value"]
        last_val = data_points[-1]["value"]
        if first_val != 0:
            change_pct = round((last_val - first_val) / first_val * 100, 1)
        if change_pct is not None:
            trend_direction = "up" if change_pct > 0 else "down" if change_pct < 0 else "flat"

    # Determine unit from existing data
    unit = None
    snapshot = await svc.get_snapshot(str(workspace_id))
    for m in snapshot:
        if m.metric_name == metric_name:
            unit = m.unit
            break

    return MetricTrendResponse(
        metric_name=metric_name,
        unit=unit,
        data_points=[MetricTrendPoint(**dp) for dp in data_points],
        change_pct=change_pct,
        trend_direction=trend_direction,
    )


@router.get("/summary", response_model=MetricSummaryResponse)
async def get_summary(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取指标文本摘要（供 AI 使用）"""
    await require_workspace_role(str(workspace_id), current_user, "viewer", db)
    svc = BusinessMetricsService(db)
    summary = await svc.get_ai_analysis_context(str(workspace_id))
    categories = await svc.list_categories(str(workspace_id))
    snapshot = await svc.get_snapshot(str(workspace_id))
    return MetricSummaryResponse(
        summary_text=summary,
        metric_count=len(snapshot),
        categories=categories,
    )
