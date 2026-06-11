"""Tool: Query Business Metrics (Digital Twin) — actual DB-backed implementation"""

import asyncio
import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _query_sync(metric_names: str | None, category: str | None) -> str:
    """Synchronous wrapper that runs async DB query in event loop"""
    async def _run():
        try:
            from app.database import AsyncSessionLocal
            from sqlalchemy import select, func
            from app.models.business_metrics import BusinessMetric
            async with AsyncSessionLocal() as s:
                # Get latest metric per metric_name using DISTINCT ON
                subq = (
                    select(
                        BusinessMetric.metric_name,
                        func.max(BusinessMetric.recorded_at).label("max_ts")
                    )
                    .group_by(BusinessMetric.metric_name)
                    .subquery()
                )
                stmt = (
                    select(BusinessMetric)
                    .join(subq, (BusinessMetric.metric_name == subq.c.metric_name) & (BusinessMetric.recorded_at == subq.c.max_ts))
                    .order_by(BusinessMetric.metric_name)
                )
                result = await s.execute(stmt)
                rows = result.scalars().all()
                if not rows:
                    return "No business metrics found. Record metrics in Settings > Metrics first."

                lines = ["Current Business Metrics Snapshot:"]
                for m in rows:
                    if metric_names:
                        names = [n.strip().lower() for n in metric_names.split(",")]
                        if m.metric_name.lower() not in names:
                            continue
                    if category and m.category != category:
                        continue
                    parts = [f"- {m.metric_name}: {m.metric_value}"]
                    if m.unit:
                        parts.append(f" {m.unit}")
                    if m.period:
                        parts.append(f" (period: {m.period})")
                    lines.append("".join(parts))

                if len(lines) == 1:
                    return "No matching metrics found for the given filters."
                return "\n".join(lines)
        except Exception as e:
            logger.warning(f"query_metrics tool error: {e}")
            return f"Unable to query metrics at this time. Metrics data may be available in the conversation context."

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(_run())


def _trend_sync(metric_name: str, periods: int) -> str:
    """Synchronous wrapper for trend query"""
    async def _run():
        try:
            from app.database import AsyncSessionLocal
            from app.services.business_metrics_service import BusinessMetricsService
            async with AsyncSessionLocal() as s:
                svc = BusinessMetricsService(s)
                # We need workspace_id but tool doesn't have it — query across all workspaces
                from sqlalchemy import select
                from app.models.business_metrics import BusinessMetric
                result = await s.execute(
                    select(BusinessMetric)
                    .where(BusinessMetric.metric_name == metric_name)
                    .order_by(BusinessMetric.recorded_at.desc())
                    .limit(periods)
                )
                rows = list(result.scalars().all())
                if not rows:
                    return f"No trend data found for '{metric_name}'."

                rows = list(reversed(rows))
                lines = [f"Trend for '{metric_name}' (last {len(rows)} periods):"]
                for r in rows:
                    period_str = r.period or r.recorded_at.strftime("%Y-%m") if r.recorded_at else "N/A"
                    lines.append(f"  {period_str}: {r.metric_value}" + (f" {r.unit}" if r.unit else ""))

                if len(rows) >= 2:
                    first = rows[0].metric_value
                    last = rows[-1].metric_value
                    if first != 0:
                        change = round((last - first) / first * 100, 1)
                        direction = "↑" if change > 0 else "↓" if change < 0 else "→"
                        lines.append(f"  Change: {direction} {change}%")
                return "\n".join(lines)
        except Exception as e:
            logger.warning(f"get_metric_trend tool error: {e}")
            return f"Unable to query trend data at this time."

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(_run())


@tool
def query_metrics(metric_names: str | None = None, category: str | None = None) -> str:
    """Query current business metrics from the Digital Twin.

    Args:
        metric_names: Optional comma-separated metric names to query (e.g., "revenue,orders"). If None, returns all.
        category: Optional category filter (e.g., "revenue", "cost", "inventory", "hr", "operations")

    Returns:
        Formatted text with current metric values.
    """
    return _query_sync(metric_names, category)


@tool
def get_metric_trend(metric_name: str, periods: int = 6) -> str:
    """Get historical trend data for a specific business metric.

    Args:
        metric_name: The metric to get trend for (e.g., "revenue", "inventory_level")
        periods: Number of periods to look back (default 6)

    Returns:
        Time series data with period-to-period changes.
    """
    return _trend_sync(metric_name, periods)
