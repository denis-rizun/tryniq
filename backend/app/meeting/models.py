from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel
from sqlmodel._compat import SQLModelConfig

from app.core.database import IDMixin, TimestampMixin
from app.meeting.constants import MeetingStatus


class MeetingRoom(IDMixin, TimestampMixin, SQLModel, table=True):
    __tablename__ = "meeting_room"
    model_config = SQLModelConfig(extra="allow")

    meet_code: str = Field(unique=True, index=True)
    title: str


class Meeting(IDMixin, SQLModel, table=True):
    __tablename__ = "meeting"
    model_config = SQLModelConfig(extra="allow")

    title: str
    status: MeetingStatus = Field(default=MeetingStatus.LIVE)
    started_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), sa_type=DateTime(timezone=True))
    ended_at: datetime | None = Field(sa_type=DateTime(timezone=True), nullable=True)

    room_id: UUID = Field(foreign_key="meeting_room.id", index=True)
    room: MeetingRoom = Relationship(sa_relationship_kwargs={"lazy": "raise"})
