"""add meeting metadata columns (summary, summary_embedding, generated_at)

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-05

"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("meeting", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("meeting", sa.Column("summary_embedding", Vector(1536), nullable=True))
    op.add_column(
        "meeting",
        sa.Column("metadata_generated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "CREATE INDEX meeting_summary_embedding_idx ON meeting "
        "USING ivfflat (summary_embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS meeting_summary_embedding_idx")
    op.drop_column("meeting", "metadata_generated_at")
    op.drop_column("meeting", "summary_embedding")
    op.drop_column("meeting", "summary")
