"""数字孪生 — Pydantic Schema"""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ── Create ──────────────────────────────────────────────

class MetricCreate(BaseModel):
    """创建/记录单个业务指标"""
    metric_name: str = Field(..., max_length=100, description="指标名称，如 revenue/orders/inventory")
    metric_value: float = Field(..., description="指标数值")
    unit: Optional[str] = Field(None, max_length=50, description="单位，如 USD/units/hours")
    period: Optional[str] = Field(None, max_length=50, description="周期，如 2026-06/2026-Q2")
    recorded_at: Optional[datetime] = Field(None, description="记录时间，默认当前时间")
    category: Optional[str] = Field(None, max_length=50, description="分类：revenue/cost/inventory/hr/operations/custom")
    tags: dict = Field(default_factory=dict, description="自定义标签")
    notes: Optional[str] = Field(None, description="备注")


class MetricBatchCreate(BaseModel):
    """批量记录业务指标"""
    metrics: list[MetricCreate] = Field(..., min_length=1, max_length=100)


# ── Update ──────────────────────────────────────────────

class MetricUpdate(BaseModel):
    """更新业务指标（仅可变字段）"""
    metric_value: Optional[float] = None
    notes: Optional[str] = None


# ── Response ────────────────────────────────────────────

class MetricResponse(BaseModel):
    """单个指标响应"""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    metric_name: str
    metric_value: float
    unit: Optional[str] = None
    period: Optional[str] = None
    recorded_at: Optional[datetime] = None
    category: Optional[str] = None
    tags: dict = {}
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class MetricListResponse(BaseModel):
    """指标列表响应"""
    metrics: list[MetricResponse]
    total: int


class MetricSnapshot(BaseModel):
    """最新指标快照 — 每个 metric_name 的最新值"""
    company_id: str
    metrics: list[MetricResponse]
    generated_at: Optional[str] = None


class MetricTrendPoint(BaseModel):
    """趋势数据点"""
    period: str
    value: float
    recorded_at: Optional[str] = None


class MetricTrendResponse(BaseModel):
    """指标趋势响应"""
    metric_name: str
    unit: Optional[str] = None
    data_points: list[MetricTrendPoint]
    change_pct: Optional[float] = None  # 最新 vs 最早的变化百分比
    trend_direction: Optional[str] = None  # "up" / "down" / "flat"


class MetricSummaryResponse(BaseModel):
    """指标文本摘要（供 AI 使用）"""
    summary_text: str
    metric_count: int
    categories: list[str]
