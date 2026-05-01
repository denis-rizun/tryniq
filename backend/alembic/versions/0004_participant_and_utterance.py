"""create participant and utterance

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-01

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "participant",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("stream_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("is_local_user", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name=op.f("participant_pkey")),
        sa.ForeignKeyConstraint(["meeting_id"], ["meeting.id"], name=op.f("participant_meeting_id_fkey")),
        sa.UniqueConstraint("meeting_id", "stream_id", name="participant_meeting_stream_key"),
    )
    op.create_index(op.f("participant_meeting_id_idx"), "participant", ["meeting_id"], unique=False)
    op.create_index(op.f("participant_stream_id_idx"), "participant", ["stream_id"], unique=False)

    op.create_table(
        "utterance",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("stream_id", sa.Uuid(), nullable=False),
        sa.Column("t_start", sa.Float(), nullable=False),
        sa.Column("t_end", sa.Float(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("word_timings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_final", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name=op.f("utterance_pkey")),
        sa.ForeignKeyConstraint(["meeting_id"], ["meeting.id"], name=op.f("utterance_meeting_id_fkey")),
        sa.ForeignKeyConstraint(["participant_id"], ["participant.id"], name=op.f("utterance_participant_id_fkey")),
    )
    op.create_index(op.f("utterance_meeting_id_idx"), "utterance", ["meeting_id"], unique=False)
    op.create_index(op.f("utterance_participant_id_idx"), "utterance", ["participant_id"], unique=False)
    op.create_index(op.f("utterance_stream_id_idx"), "utterance", ["stream_id"], unique=False)
    op.create_index("utterance_meeting_t_start_idx", "utterance", ["meeting_id", "t_start"], unique=False)


def downgrade() -> None:
    op.drop_index("utterance_meeting_t_start_idx", table_name="utterance")
    op.drop_index(op.f("utterance_stream_id_idx"), table_name="utterance")
    op.drop_index(op.f("utterance_participant_id_idx"), table_name="utterance")
    op.drop_index(op.f("utterance_meeting_id_idx"), table_name="utterance")
    op.drop_table("utterance")

    op.drop_index(op.f("participant_stream_id_idx"), table_name="participant")
    op.drop_index(op.f("participant_meeting_id_idx"), table_name="participant")
    op.drop_table("participant")
