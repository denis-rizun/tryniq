from datetime import UTC, datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel
from sqlmodel._compat import SQLModelConfig

from app.chat.constants import CHAT_EMBEDDING_DIM, ChatRole, ChatScope
from app.core.database import IDMixin, TimestampMixin


class UtteranceEmbedding(SQLModel, table=True):
    __tablename__ = "utterance_embedding"
    model_config = SQLModelConfig(extra="allow")

    utterance_id: UUID = Field(primary_key=True, foreign_key="utterance.id")
    meeting_id: UUID = Field(foreign_key="meeting.id", index=True)
    embedding: list[float] = Field(sa_column=Column(Vector(CHAT_EMBEDDING_DIM), nullable=False))
    model: str = Field(nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        sa_type=DateTime(timezone=True),
        nullable=False,
    )


class ChatSession(IDMixin, TimestampMixin, SQLModel, table=True):
    __tablename__ = "chat_session"

    title: str
    scope: ChatScope = Field(index=True)
    meeting_id: UUID | None = Field(default=None, foreign_key="meeting.id", index=True)


class ChatMessage(IDMixin, SQLModel, table=True):
    __tablename__ = "chat_message"

    session_id: UUID = Field(foreign_key="chat_session.id", index=True)
    role: ChatRole
    text: str
    citations: list[dict] = Field(default_factory=list, sa_column=Column(JSONB, nullable=False))
    model: str
    latency_ms: int
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        sa_type=DateTime(timezone=True),
        nullable=False,
    )
