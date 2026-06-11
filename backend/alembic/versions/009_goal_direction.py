"""Goals 方向字段 — 支持 "higher"（越高越好）和 "lower"（越低越好）

Revision ID: 009
Create Date: 2026-06-10
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    op.add_column("company_goals",
        sa.Column("direction", sa.String(10), server_default="higher", nullable=False))


def downgrade():
    op.drop_column("company_goals", "direction")
