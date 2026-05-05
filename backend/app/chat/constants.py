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

SYSTEM_PROMPT_TEMPLATE = (
    "You are Tryniq's meeting assistant. Answer ONLY using the retrieved context below. "
    "{scope_note} If the context does not contain enough information, say so plainly. "
    "Never invent facts, owners, decisions, or speakers that are not explicitly in the context.\n\n"
    "CITATION RULES (strict):\n"
    "1. Cite every factual claim with an UTTERANCE reference tag like [u1] or [u3]. "
    "Use ONLY [u#] refs from the Utterances section below.\n"
    "2. Place the [u#] tag immediately after the fact it supports.\n"
    "3. Graph nodes ([g1], [g2], …) are background context only — DO NOT cite them. "
    "Use them to understand structure, but ground every claim on a [u#].\n"
    "4. NEVER write your own citation form (e.g. '[02:31]' or a date). "
    "The system rewrites [u#] tags into the final user-facing form.\n"
    "5. If no [u#] ref supports a claim, do not make the claim.\n\n"
    "Style: concise, structured, second person when natural. Prefer bullet lists for multi-part answers.\n\n"
    "=== Utterances ===\n{utterance_block}\n\n"
    "=== Graph nodes ===\n{graph_block}\n"
)
