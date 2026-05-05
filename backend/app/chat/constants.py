import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from app.chat.schemas import ChatCitation


class ChatScope(StrEnum):
    MEETING = "meeting"
    ALL = "all"


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatStreamEventKind(StrEnum):
    MESSAGE_STARTED = "message_started"
    TOKEN = "token"
    MESSAGE_COMPLETED = "message_completed"
    ERROR = "error"


CHAT_EMBEDDING_DIM = 1536
CHAT_TITLE_MAX_LEN = 80
CHAT_RETRIEVAL_GRAPH_TYPES: tuple[str, ...] = ("Decision", "ActionItem", "OpenQuestion", "Topic")
CROSS_LABEL_MAX_LEN = 40

REF_PATTERN = re.compile(r"\[(u\d+)\]")  # noqa
GRAPH_REF_PATTERN = re.compile(r"\s*\[g\d+\]")  # noqa


@dataclass(slots=True)
class AnswerHistoryMessage:
    role: str
    text: str


@dataclass(slots=True)
class AnswerDelta:
    text: str


@dataclass(slots=True)
class AnswerComplete:
    text: str
    citations: "list[ChatCitation]"
    model: str


type AnswerEvent = AnswerDelta | AnswerComplete


@dataclass(slots=True)
class UtteranceHit:
    ref: str
    utterance_id: UUID
    meeting_id: UUID
    meeting_title: str | None
    meeting_started_at: datetime | None
    speaker: str | None
    t_start: float
    t_end: float
    text: str
    score: float


@dataclass(slots=True)
class GraphHit:
    ref: str
    node_id: UUID
    meeting_id: UUID
    meeting_title: str | None
    meeting_started_at: datetime | None
    type: str
    text: str
    score: float


@dataclass(slots=True)
class RetrievedContext:
    utterances: list[UtteranceHit]
    graph_nodes: list[GraphHit]

    def is_empty(self) -> bool:
        return not self.utterances and not self.graph_nodes


SCOPE_NOTE_MEETING = "You are answering about ONE specific meeting."
SCOPE_NOTE_ALL = "You are answering across MULTIPLE finalized meetings."
