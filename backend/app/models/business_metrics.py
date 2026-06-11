"""数字孪生 — 企业业务指标模型"""

import uuid
from datetime import datetime

from sqlalchemy import String, Float, Text, DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BusinessMetric(Base):
    """企业业务指标 — Digital Twin 核心数据表"""

    __tablename__ = "business_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    period: Mapped[str | None] = mapped_column(String(50), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tags: Mapped[dict] = mapped_column(JSONB, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="business_metrics", lazy="selectin")

    __table_args__ = (
        Index("idx_metrics_company_name_period", "company_id", "metric_name", "period"),
        Index("idx_metrics_category", "category"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "company_id": str(self.company_id),
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "unit": self.unit,
            "period": self.period,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "category": self.category,
            "tags": self.tags,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
