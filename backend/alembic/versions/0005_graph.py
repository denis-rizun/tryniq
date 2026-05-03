"""create graph_node and graph_edge

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-03

"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


node_type = postgresql.ENUM(
    "Meeting",
    "Person",
    "Topic",
    "Decision",
    "ActionItem",
    "OpenQuestion",
    "Entity",
    "Utterance",
    name="nodetype",
    create_type=False,
)
edge_type = postgresql.ENUM(
    "PARTICIPATED_IN",
    "DISCUSSED_IN",
    "MADE_DECISION",
    "ASSIGNED_TO",
    "BLOCKS",
    "ABOUT_TOPIC",
    "MENTIONS",
    "SOURCE",
    "RELATES_TO",
    name="edgetype",
    create_type=False,
)
node_status = postgresql.ENUM(
    "provisional",
    "confirmed",
    "superseded",
    name="nodestatus",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    node_type.create(bind, checkfirst=True)
    edge_type.create(bind, checkfirst=True)
    node_status.create(bind, checkfirst=True)

    op.create_table(
        "graph_node",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("type", node_type, nullable=False),
        sa.Column("fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", node_status, nullable=False, server_default=sa.text("'provisional'")),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name=op.f("graph_node_pkey")),
        sa.ForeignKeyConstraint(["meeting_id"], ["meeting.id"], name=op.f("graph_node_meeting_id_fkey")),
    )
    op.create_index(op.f("graph_node_meeting_id_idx"), "graph_node", ["meeting_id"], unique=False)
    op.create_index(op.f("graph_node_type_idx"), "graph_node", ["type"], unique=False)
    op.create_index("graph_node_meeting_type_idx", "graph_node", ["meeting_id", "type"], unique=False)
    op.execute(
        "CREATE INDEX graph_node_embedding_idx ON graph_node "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    op.create_table(
        "graph_edge",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("type", edge_type, nullable=False),
        sa.Column("from_id", sa.Uuid(), nullable=False),
        sa.Column("to_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name=op.f("graph_edge_pkey")),
        sa.ForeignKeyConstraint(["meeting_id"], ["meeting.id"], name=op.f("graph_edge_meeting_id_fkey")),
        sa.ForeignKeyConstraint(
            ["from_id"], ["graph_node.id"], name=op.f("graph_edge_from_id_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["to_id"], ["graph_node.id"], name=op.f("graph_edge_to_id_fkey"), ondelete="CASCADE"),
    )
    op.create_index(op.f("graph_edge_meeting_id_idx"), "graph_edge", ["meeting_id"], unique=False)
    op.create_index(op.f("graph_edge_type_idx"), "graph_edge", ["type"], unique=False)
    op.create_index(op.f("graph_edge_from_id_idx"), "graph_edge", ["from_id"], unique=False)
    op.create_index(op.f("graph_edge_to_id_idx"), "graph_edge", ["to_id"], unique=False)
    op.create_index("graph_edge_meeting_type_idx", "graph_edge", ["meeting_id", "type"], unique=False)


def downgrade() -> None:
    op.drop_index("graph_edge_meeting_type_idx", table_name="graph_edge")
    op.drop_index(op.f("graph_edge_to_id_idx"), table_name="graph_edge")
    op.drop_index(op.f("graph_edge_from_id_idx"), table_name="graph_edge")
    op.drop_index(op.f("graph_edge_type_idx"), table_name="graph_edge")
    op.drop_index(op.f("graph_edge_meeting_id_idx"), table_name="graph_edge")
    op.drop_table("graph_edge")

    op.execute("DROP INDEX IF EXISTS graph_node_embedding_idx")
    op.drop_index("graph_node_meeting_type_idx", table_name="graph_node")
    op.drop_index(op.f("graph_node_type_idx"), table_name="graph_node")
    op.drop_index(op.f("graph_node_meeting_id_idx"), table_name="graph_node")
    op.drop_table("graph_node")

    bind = op.get_bind()
    edge_type.drop(bind, checkfirst=True)
    node_status.drop(bind, checkfirst=True)
    node_type.drop(bind, checkfirst=True)
