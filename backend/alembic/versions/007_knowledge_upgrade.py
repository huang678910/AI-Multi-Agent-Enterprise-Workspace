"""知识中心升级 — document_chunks 增加来源/内容类型/父块字段

Revision ID: 007
Create Date: 2026-06-07
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    # Add source_type to document_chunks
    op.add_column("document_chunks",
        sa.Column("source_type", sa.String(50), server_default="upload", nullable=False))
    # Add content_type to document_chunks
    op.add_column("document_chunks",
        sa.Column("content_type", sa.String(50), server_default="text", nullable=False))
    # Add parent_chunk_id for related chunks (e.g., table belonging to a paragraph)
    op.add_column("document_chunks",
        sa.Column("parent_chunk_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("idx_chunks_source_type", "document_chunks", ["source_type"])
    op.create_index("idx_chunks_content_type", "document_chunks", ["content_type"])

    # Add source_type to documents table too
    op.add_column("documents",
        sa.Column("source_type", sa.String(50), server_default="upload", nullable=False))


def downgrade():
    op.drop_column("documents", "source_type")
    op.drop_column("document_chunks", "parent_chunk_id")
    op.drop_column("document_chunks", "content_type")
    op.drop_column("document_chunks", "source_type")
