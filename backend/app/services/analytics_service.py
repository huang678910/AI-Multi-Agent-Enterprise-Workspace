"""企业分析中心 — 聚合 metrics + KPIs + Goals + AI 分析（带缓存）"""

import logging
import time as _time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.business_metrics_service import BusinessMetricsService
from app.services.llm_service import _get_llm
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

# In-memory cache (TTL-based)
_analysis_cache: dict[str, tuple[float, dict]] = {}
CACHE_TTL = 3600  # 1 hour


class AnalyticsService:

    def __init__(self, db: AsyncSession, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id

    def _cache_key(self) -> str:
        return f"analytics:ai_analysis:{self.workspace_id}"

    def _get_cached(self) -> dict | None:
        """从内存缓存读取（带 TTL 检查）"""
        key = self._cache_key()
        if key in _analysis_cache:
            expiry, data = _analysis_cache[key]
            if _time.time() < expiry:
                return data
            del _analysis_cache[key]  # Expired
        return None

    def _set_cached(self, analysis: dict) -> None:
        """写入内存缓存"""
        _analysis_cache[self._cache_key()] = (_time.time() + CACHE_TTL, analysis)

    async def get_dashboard_data(self) -> dict:
        """聚合仪表盘所需的所有数据"""
        metrics_svc = BusinessMetricsService(self.db)

        # 1. Metrics snapshot
        snapshot_metrics = await metrics_svc.get_snapshot(self.workspace_id)
        snapshot = {
            "company_id": self.workspace_id,
            "metrics": [m.to_dict() for m in snapshot_metrics],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        # 2. Trends for top metrics
        trends = {}
        top_metrics = snapshot_metrics[:6]
        for m in top_metrics:
            data_points = await metrics_svc.get_trend(self.workspace_id, m.metric_name)
            if len(data_points) >= 2:
                first = data_points[0]["value"]
                last = data_points[-1]["value"]
                change_pct = round((last - first) / first * 100, 1) if first != 0 else 0
                trend_dir = "up" if change_pct > 0 else "down" if change_pct < 0 else "flat"
            else:
                change_pct = None
                trend_dir = "flat"
            trends[m.metric_name] = {
                "metric_name": m.metric_name,
                "unit": m.unit,
                "data_points": data_points,
                "change_pct": change_pct,
                "trend_direction": trend_dir,
            }

        # 3. KPIs from Layer 1
        from app.models.company import Company, CompanyKPI, CompanyGoal
        from sqlalchemy import select
        company_result = await self.db.execute(
            select(Company).where(Company.workspace_id == self.workspace_id)
        )
        company = company_result.scalar_one_or_none()
        kpis = []
        goals = []
        if company:
            kpi_result = await self.db.execute(
                select(CompanyKPI).where(CompanyKPI.company_id == company.id)
            )
            kpis = [
                {
                    "id": str(k.id), "name": k.name, "category": k.category,
                    "current_value": k.current_value, "target_value": k.target_value,
                    "unit": k.unit, "period": k.period,
                    "last_updated": k.last_updated.isoformat() if k.last_updated else None,
                }
                for k in kpi_result.scalars().all()
            ]
            goal_result = await self.db.execute(
                select(CompanyGoal).where(CompanyGoal.company_id == company.id)
            )
            goals = [
                {
                    "id": str(g.id), "type": g.type, "title": g.title,
                    "description": g.description, "target_value": g.target_value,
                    "current_value": g.current_value, "progress_pct": g.progress_pct,
                    "start_date": g.start_date.isoformat() if g.start_date else None,
                    "end_date": g.end_date.isoformat() if g.end_date else None,
                    "status": g.status, "direction": g.direction,
                }
                for g in goal_result.scalars().all()
            ]

        alerts = self._check_alerts(snapshot_metrics, kpis, goals)

        return {
            "metrics_snapshot": snapshot,
            "trends": trends,
            "kpis": kpis,
            "goals": goals,
            "analysis": None,
            "alerts": alerts,
        }

    def _check_alerts(self, metrics: list, kpis: list, goals: list) -> list[dict]:
        """Rule-based alert generation"""
        alerts = []

        for kpi in kpis:
            if kpi["target_value"] and kpi["current_value"]:
                ratio = kpi["current_value"] / kpi["target_value"] if kpi["target_value"] != 0 else 1
                if ratio < 0.5:
                    alerts.append({
                        "id": f"kpi_{kpi['id']}", "severity": "critical",
                        "metric_name": kpi["name"],
                        "message": f"{kpi['name']} is at {ratio*100:.0f}% of target ({kpi['current_value']} vs {kpi['target_value']} {kpi.get('unit','')})",
                        "threshold": kpi["target_value"],
                    })
                elif ratio < 0.8:
                    alerts.append({
                        "id": f"kpi_{kpi['id']}", "severity": "warning",
                        "metric_name": kpi["name"],
                        "message": f"{kpi['name']} is at {ratio*100:.0f}% of target",
                        "threshold": kpi["target_value"],
                    })

        for goal in goals:
            if goal["progress_pct"] is not None and goal["progress_pct"] < 30 and goal["status"] == "active":
                alerts.append({
                    "id": f"goal_{goal['id']}", "severity": "warning",
                    "metric_name": goal["title"],
                    "message": f"Goal '{goal['title']}' is only {goal['progress_pct']:.0f}% complete",
                    "threshold": None,
                })

        return alerts

    async def generate_ai_analysis(self, dashboard_data: dict | None = None, force_refresh: bool = False) -> dict:
        """调用 LLM 生成 AI 分析（内存缓存 1 小时）"""
        # Check cache first
        if not force_refresh:
            cached = self._get_cached()
            if cached:
                logger.info(f"AI analysis returned from cache for workspace {self.workspace_id}")
                return cached

        if dashboard_data is None:
            dashboard_data = await self.get_dashboard_data()

        context_lines = ["Current Business Snapshot:"]
        metrics = dashboard_data.get("metrics_snapshot", {}).get("metrics", [])
        if metrics:
            for m in metrics:
                parts = [f"- {m.get('metric_name', 'unknown')}: {m.get('metric_value', 'N/A')}"]
                if m.get("unit"):
                    parts.append(f" {m.get('unit')}")
                context_lines.append("".join(parts))

        kpis = dashboard_data.get("kpis", [])
        if kpis:
            context_lines.append("\nKPIs:")
            for k in kpis:
                context_lines.append(f"- {k['name']}: current={k['current_value']}, target={k['target_value']} {k.get('unit','')}")

        goals = dashboard_data.get("goals", [])
        if goals:
            context_lines.append("\nGoals:")
            for g in goals:
                context_lines.append(f"- [{g['status']}] {g['title']}: progress={g['progress_pct']}%")

        alerts = dashboard_data.get("alerts", [])
        if alerts:
            context_lines.append("\n⚠️ Alerts:")
            for a in alerts:
                context_lines.append(f"- [{a['severity']}] {a['message']}")

        context = "\n".join(context_lines)
        prompt = f"""As a business analyst, review the following business data and provide a concise analysis.

{context}

Please provide:
1. **Summary**: Overall business health assessment (2-3 sentences)
2. **Key Insights**: 3-5 specific observations from the data
3. **Recommendations**: 2-3 actionable suggestions based on the data

Be data-driven, specific, and concise. If there is very little data, note what additional metrics would be helpful."""

        try:
            llm = _get_llm(streaming=False)
            messages = [
                SystemMessage(content="You are a business analytics AI. Provide data-driven analysis and actionable recommendations. Be concise and specific."),
                HumanMessage(content=prompt),
            ]
            response = await llm.ainvoke(messages)
            text = response.content.strip()

            insights = []
            recommendations = []
            current_section = ""
            for line in text.split("\n"):
                line = line.strip()
                if "**Summary**" in line or "summary" in line.lower():
                    current_section = "summary"
                elif "**Key Insights**" in line or "insight" in line.lower():
                    current_section = "insights"
                elif "**Recommendations**" in line or "recommendation" in line.lower():
                    current_section = "recommendations"
                elif line.startswith("- ") or line.startswith("* "):
                    if current_section == "insights":
                        insights.append(line.lstrip("- *"))
                    elif current_section == "recommendations":
                        recommendations.append(line.lstrip("- *"))

            result = {
                "summary": text[:500],
                "insights": insights[:5],
                "recommendations": recommendations[:3],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._set_cached(result)
            return result
        except Exception as e:
            logger.error(f"AI analysis generation failed: {e}")
            return {
                "summary": f"AI analysis unavailable: {e}",
                "insights": [],
                "recommendations": [],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
