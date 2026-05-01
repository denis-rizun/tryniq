from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel
from sqlmodel._compat import SQLModelConfig

from app.core.database import IDMixin, TimestampMixin


class Participant(IDMixin, TimestampMixin, SQLModel, table=True):
    __tablename__ = "participant"
    __table_args__ = (UniqueConstraint("meeting_id", "stream_id", name="participant_meeting_stream_key"),)
    model_config = SQLModelConfig(extra="allow")

    meeting_id: UUID = Field(foreign_key="meeting.id", index=True)
    stream_id: UUID = Field(index=True)
    name: str
    is_local_user: bool = Field(default=False)
