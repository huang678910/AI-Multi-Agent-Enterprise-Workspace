"""数字孪生 — 业务指标 CRUD + 快照 + 趋势分析"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.business_metrics import BusinessMetric

logger = logging.getLogger(__name__)


class BusinessMetricsService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_company(self, workspace_id: str) -> Company | None:
        """查找 workspace 对应的 company"""
        result = await self.db.execute(
            select(Company).where(Company.workspace_id == workspace_id)
        )
        return result.scalar_one_or_none()

    # ── CRUD ──────────────────────────────────────────────

    async def record(self, workspace_id: str, data: dict) -> BusinessMetric:
        """记录单个业务指标"""
        company = await self._get_company(workspace_id)
        if not company:
            raise ValueError("Company profile not found. Create a company profile first.")

        metric = BusinessMetric(
            company_id=company.id,
            metric_name=data["metric_name"],
            metric_value=data["metric_value"],
            unit=data.get("unit"),
            period=data.get("period"),
            recorded_at=data.get("recorded_at") or datetime.now(timezone.utc),
            category=data.get("category"),
            tags=data.get("tags", {}),
            notes=data.get("notes"),
        )
        self.db.add(metric)
        await self.db.flush()
        await self.db.refresh(metric)
        return metric

    async def batch_record(self, workspace_id: str, metrics_data: list[dict]) -> list[BusinessMetric]:
        """批量记录业务指标"""
        company = await self._get_company(workspace_id)
        if not company:
            raise ValueError("Company profile not found.")

        metrics = []
        for data in metrics_data:
            metric = BusinessMetric(
                company_id=company.id,
                metric_name=data["metric_name"],
                metric_value=data["metric_value"],
                unit=data.get("unit"),
                period=data.get("period"),
                recorded_at=data.get("recorded_at") or datetime.now(timezone.utc),
                category=data.get("category"),
                tags=data.get("tags", {}),
                notes=data.get("notes"),
            )
            self.db.add(metric)
            metrics.append(metric)
        await self.db.flush()
        return metrics

    async def update(self, metric_id: str, data: dict) -> BusinessMetric | None:
        """更新指标值"""
        result = await self.db.execute(
            select(BusinessMetric).where(BusinessMetric.id == metric_id)
        )
        metric = result.scalar_one_or_none()
        if not metric:
            return None
        if "metric_value" in data and data["metric_value"] is not None:
            metric.metric_value = data["metric_value"]
        if "notes" in data:
            metric.notes = data["notes"]
        await self.db.flush()
        await self.db.refresh(metric)
        return metric

    async def delete(self, metric_id: str) -> bool:
        """删除一条指标记录"""
        result = await self.db.execute(
            select(BusinessMetric).where(BusinessMetric.id == metric_id)
        )
        metric = result.scalar_one_or_none()
        if not metric:
            return False
        await self.db.delete(metric)
        await self.db.flush()
        return True

    # ── 查询 ──────────────────────────────────────────────

    async def get_snapshot(self, workspace_id: str) -> list[BusinessMetric]:
        """获取最新指标快照 — 每个 metric_name 取最新一条"""
        company = await self._get_company(workspace_id)
        if not company:
            return []

        # Use DISTINCT ON to get latest per metric_name
        subq = (
            select(
                BusinessMetric.metric_name,
                func.max(BusinessMetric.recorded_at).label("max_recorded")
            )
            .where(BusinessMetric.company_id == company.id)
            .group_by(BusinessMetric.metric_name)
            .subquery()
        )
        result = await self.db.execute(
            select(BusinessMetric)
            .join(subq, (BusinessMetric.metric_name == subq.c.metric_name) & (BusinessMetric.recorded_at == subq.c.max_recorded))
            .where(BusinessMetric.company_id == company.id)
            .order_by(BusinessMetric.metric_name)
        )
        return result.scalars().all()

    async def get_trend(self, workspace_id: str, metric_name: str, periods: int = 12) -> list[dict]:
        """获取某个指标的时间序列"""
        company = await self._get_company(workspace_id)
        if not company:
            return []

        result = await self.db.execute(
            select(BusinessMetric)
            .where(
                BusinessMetric.company_id == company.id,
                BusinessMetric.metric_name == metric_name,
            )
            .order_by(BusinessMetric.recorded_at.desc())
            .limit(periods)
        )
        rows = result.scalars().all()
        # Return in chronological order
        rows = list(reversed(rows))
        return [
            {
                "period": r.period or r.recorded_at.strftime("%Y-%m"),
                "value": r.metric_value,
                "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
            }
            for r in rows
        ]

    async def list_by_workspace(self, workspace_id: str, category: str | None = None) -> list[BusinessMetric]:
        """列出 workspace 下所有指标（按时间倒序）"""
        company = await self._get_company(workspace_id)
        if not company:
            return []

        stmt = (
            select(BusinessMetric)
            .where(BusinessMetric.company_id == company.id)
            .order_by(BusinessMetric.recorded_at.desc())
        )
        if category:
            stmt = stmt.where(BusinessMetric.category == category)
        result = await self.db.execute(stmt.limit(200))
        return result.scalars().all()

    async def list_categories(self, workspace_id: str) -> list[str]:
        """列出已使用的分类"""
        company = await self._get_company(workspace_id)
        if not company:
            return []

        result = await self.db.execute(
            select(BusinessMetric.category)
            .where(BusinessMetric.company_id == company.id)
            .where(BusinessMetric.category.isnot(None))
            .distinct()
        )
        return [r[0] for r in result.all() if r[0]]

    # ── AI 上下文 ─────────────────────────────────────────

    async def get_ai_analysis_context(self, workspace_id: str) -> str:
        """生成 AI 可用的文本摘要（注入到 Agent 上下文）"""
        company = await self._get_company(workspace_id)
        if not company:
            return ""

        snapshot = await self.get_snapshot(workspace_id)
        if not snapshot:
            return ""

        lines = [f"Business Metrics Snapshot (company: {company.name}):"]
        for m in snapshot:
            parts = [f"{m.metric_name}: {m.metric_value}"]
            if m.unit:
                parts.append(f" {m.unit}")
            if m.period:
                parts.append(f" (period: {m.period})")
            if m.category:
                parts.append(f" [{m.category}]")
            lines.append("".join(parts))

        # Add simple revenue/cost summary if present
        revenue_metrics = [m for m in snapshot if m.category == "revenue" or "revenue" in m.metric_name.lower()]
        cost_metrics = [m for m in snapshot if m.category == "cost" or "cost" in m.metric_name.lower()]

        if revenue_metrics:
            total_rev = sum(m.metric_value for m in revenue_metrics)
            lines.append(f"\nTotal Revenue: {total_rev:,.2f}")
        if cost_metrics:
            total_cost = sum(m.metric_value for m in cost_metrics)
            lines.append(f"Total Cost: {total_cost:,.2f}")
        if revenue_metrics and cost_metrics:
            total_rev = sum(m.metric_value for m in revenue_metrics)
            total_cost = sum(m.metric_value for m in cost_metrics)
            profit = total_rev - total_cost
            margin = (profit / total_rev * 100) if total_rev > 0 else 0
            lines.append(f"Gross Profit: {profit:,.2f} (Margin: {margin:.1f}%)")

        return "\n".join(lines)
