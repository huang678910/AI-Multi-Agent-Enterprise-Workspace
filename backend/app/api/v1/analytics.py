"""企业分析中心 REST API — /api/v1/workspaces/{workspace_id}/analytics/..."""

import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_workspace_role
from app.models.user import User
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workspaces/{workspace_id}/analytics", tags=["Analytics Center"])


@router.get("/dashboard")
async def get_dashboard(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取完整仪表盘数据（快照 + 趋势 + KPIs + Goals + Alerts）"""
    await require_workspace_role(str(workspace_id), current_user, "viewer", db)
    svc = AnalyticsService(db, str(workspace_id))
    data = await svc.get_dashboard_data()
    return data


@router.post("/analyze")
async def trigger_analysis(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """触发 AI 分析，生成业务洞察和建议"""
    await require_workspace_role(str(workspace_id), current_user, "member", db)
    svc = AnalyticsService(db, str(workspace_id))
    dashboard_data = await svc.get_dashboard_data()
    analysis = await svc.generate_ai_analysis(dashboard_data)
    return analysis


@router.get("/alerts")
async def get_alerts(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前告警列表"""
    await require_workspace_role(str(workspace_id), current_user, "viewer", db)
    svc = AnalyticsService(db, str(workspace_id))
    data = await svc.get_dashboard_data()
    return data.get("alerts", [])
