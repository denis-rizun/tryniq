"""create meeting_room and link meeting

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-01

"""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meeting_room",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("meet_code", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name=op.f("meeting_room_pkey")),
        sa.UniqueConstraint("meet_code", name=op.f("meeting_room_meet_code_key")),
    )
    op.create_index(op.f("meeting_room_meet_code_idx"), "meeting_room", ["meet_code"], unique=False)

    op.drop_column("meeting", "meet_url")
    op.add_column("meeting", sa.Column("room_id", sa.Uuid(), nullable=False))
    op.create_foreign_key(
        op.f("meeting_room_id_fkey"),
        "meeting",
        "meeting_room",
        ["room_id"],
        ["id"],
    )
    op.create_index(op.f("meeting_room_id_idx"), "meeting", ["room_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("meeting_room_id_idx"), table_name="meeting")
    op.drop_constraint(op.f("meeting_room_id_fkey"), "meeting", type_="foreignkey")
    op.drop_column("meeting", "room_id")
    op.add_column("meeting", sa.Column("meet_url", sa.String(), nullable=False, server_default=""))

    op.drop_index(op.f("meeting_room_meet_code_idx"), table_name="meeting_room")
    op.drop_table("meeting_room")
