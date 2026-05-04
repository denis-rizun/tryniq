"""add upload-related meeting statuses

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-03 00:00:00.000000

"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


NEW_VALUES = ("UPLOADING", "NORMALIZING", "DIARIZING", "TRANSCRIBING")


def upgrade() -> None:
    for value in NEW_VALUES:
        op.execute(f"ALTER TYPE meetingstatus ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    pass
