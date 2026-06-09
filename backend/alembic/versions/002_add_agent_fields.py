"""添加 Agent 相关字段 — agent_type + session metadata

Revision ID: 002
Revises: 001
Create Date: 2026-05-30
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. messages 表添加 agent_type 列
    op.add_column(
        "messages",
        sa.Column("agent_type", sa.String(50), nullable=True),
    )

    # 2. chat_sessions 表添加 metadata 列
    op.add_column(
        "chat_sessions",
        sa.Column("metadata", postgresql.JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("messages", "agent_type")
    op.drop_column("chat_sessions", "metadata")
