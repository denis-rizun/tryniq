from datetime import UTC, datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.core.database import IDMixin, TimestampMixin
from app.graph.constants import EMBEDDING_DIM
from app.meeting.constants import MeetingStatus


class MeetingRoom(IDMixin, TimestampMixin, SQLModel, table=True):
    __tablename__ = "meeting_room"

    meet_code: str = Field(unique=True, index=True)
    title: str


class Meeting(IDMixin, SQLModel, table=True):
    __tablename__ = "meeting"

    title: str
    status: MeetingStatus = Field(default=MeetingStatus.LIVE)
    started_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), sa_type=DateTime(timezone=True))
    ended_at: datetime | None = Field(sa_type=DateTime(timezone=True), nullable=True)

    summary: str | None = Field(default=None, nullable=True)
    summary_embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(Vector(EMBEDDING_DIM), nullable=True),
    )
    metadata_generated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    room_id: UUID = Field(foreign_key="meeting_room.id", index=True)
    room: MeetingRoom = Relationship(sa_relationship_kwargs={"lazy": "raise"})
