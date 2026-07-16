"""create meeting

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-01 14:55:44.648516

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


meeting_status = postgresql.ENUM(
    "LIVE",
    "FINALIZING",
    "FINAL",
    "FAILED",
    name="meetingstatus",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    meeting_status.create(bind, checkfirst=True)
    op.create_table(
        "meeting",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("meet_url", sa.String(), nullable=False),
        sa.Column("status", meeting_status, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("meeting_pkey")),
    )


def downgrade() -> None:
    op.drop_table("meeting")
    bind = op.get_bind()
    meeting_status.drop(bind, checkfirst=True)
