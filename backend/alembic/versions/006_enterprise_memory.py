"""企业记忆系统 — 长期/事件/语义记忆 + 事件时间线

Revision ID: 006
Create Date: 2026-06-07
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    # --- enterprise_memories ---
    op.create_table(
        "enterprise_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("memory_type", sa.String(50), nullable=False, server_default="long_term"),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(512), nullable=True),
        sa.Column("importance", sa.Float(), server_default="5.0"),
        sa.Column("access_count", sa.Integer(), server_default="0"),
        sa.Column("last_recalled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_memories_workspace", "enterprise_memories", ["workspace_id"])
    op.create_index("idx_memories_type", "enterprise_memories", ["memory_type"])
    op.create_index("idx_memories_entity", "enterprise_memories", ["entity_type", "entity_id"])
    op.create_index("idx_memories_importance", "enterprise_memories", ["importance"])

    # --- memory_events ---
    op.create_table(
        "memory_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("related_entities", postgresql.JSONB(), server_default="[]"),
        sa.Column("impact", sa.String(50), server_default="neutral"),
        sa.Column("tags", postgresql.JSONB(), server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_events_workspace", "memory_events", ["workspace_id"])
    op.create_index("idx_events_date", "memory_events", ["event_date"])


def downgrade():
    op.drop_table("memory_events")
    op.drop_table("enterprise_memories")
