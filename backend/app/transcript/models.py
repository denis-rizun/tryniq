from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.core.database import IDMixin, TimestampMixin


class Utterance(IDMixin, TimestampMixin, SQLModel, table=True):
    __tablename__ = "utterance"

    meeting_id: UUID = Field(foreign_key="meeting.id", index=True)
    participant_id: UUID = Field(foreign_key="participant.id", index=True)
    stream_id: UUID = Field(index=True)
    t_start: float
    t_end: float
    text: str
    confidence: float | None = None
    model: str | None = None
    word_timings: list | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    is_final: bool = Field(default=True)
