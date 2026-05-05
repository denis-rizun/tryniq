"""create chat tables and utterance_embedding

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-04

"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


chat_scope = postgresql.ENUM("meeting", "all", name="chatscope", create_type=False)
chat_role = postgresql.ENUM("user", "assistant", name="chatrole", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    chat_scope.create(bind, checkfirst=True)
    chat_role.create(bind, checkfirst=True)

    op.create_table(
        "utterance_embedding",
        sa.Column("utterance_id", sa.Uuid(), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("utterance_id", name=op.f("utterance_embedding_pkey")),
        sa.ForeignKeyConstraint(
            ["utterance_id"],
            ["utterance.id"],
            name=op.f("utterance_embedding_utterance_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["meeting_id"],
            ["meeting.id"],
            name=op.f("utterance_embedding_meeting_id_fkey"),
            ondelete="CASCADE",
        ),
    )
    op.create_index(op.f("utterance_embedding_meeting_id_idx"), "utterance_embedding", ["meeting_id"], unique=False)
    op.execute(
        "CREATE INDEX utterance_embedding_embedding_idx ON utterance_embedding "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    op.create_table(
        "chat_session",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("scope", chat_scope, nullable=False),
        sa.Column("meeting_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name=op.f("chat_session_pkey")),
        sa.ForeignKeyConstraint(
            ["meeting_id"],
            ["meeting.id"],
            name=op.f("chat_session_meeting_id_fkey"),
            ondelete="SET NULL",
        ),
    )
    op.create_index(op.f("chat_session_meeting_id_idx"), "chat_session", ["meeting_id"], unique=False)
    op.create_index(op.f("chat_session_scope_idx"), "chat_session", ["scope"], unique=False)
    op.create_index("chat_session_updated_at_idx", "chat_session", [sa.text("updated_at DESC")], unique=False)

    op.create_table(
        "chat_message",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("role", chat_role, nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column(
            "citations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name=op.f("chat_message_pkey")),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["chat_session.id"],
            name=op.f("chat_message_session_id_fkey"),
            ondelete="CASCADE",
        ),
    )
    op.create_index(op.f("chat_message_session_id_idx"), "chat_message", ["session_id"], unique=False)
    op.create_index(
        "chat_message_session_created_idx",
        "chat_message",
        ["session_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("chat_message_session_created_idx", table_name="chat_message")
    op.drop_index(op.f("chat_message_session_id_idx"), table_name="chat_message")
    op.drop_table("chat_message")

    op.drop_index("chat_session_updated_at_idx", table_name="chat_session")
    op.drop_index(op.f("chat_session_scope_idx"), table_name="chat_session")
    op.drop_index(op.f("chat_session_meeting_id_idx"), table_name="chat_session")
    op.drop_table("chat_session")

    op.execute("DROP INDEX IF EXISTS utterance_embedding_embedding_idx")
    op.drop_index(op.f("utterance_embedding_meeting_id_idx"), table_name="utterance_embedding")
    op.drop_table("utterance_embedding")

    bind = op.get_bind()
    chat_role.drop(bind, checkfirst=True)
    chat_scope.drop(bind, checkfirst=True)
