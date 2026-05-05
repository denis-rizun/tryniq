from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Literal, Self
from uuid import UUID

from pydantic import Field, StringConstraints

from app.chat.constants import CHAT_TITLE_MAX_LEN, ChatRole, ChatScope, ChatStreamEventKind
from app.core.base_schema import BaseSchema

if TYPE_CHECKING:
    from app.chat.models import ChatMessage, ChatSession

NonEmptyStrippedStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
TitleStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=CHAT_TITLE_MAX_LEN)]
PREVIEW_MAX_LEN = 140


class ChatCitation(BaseSchema):
    utterance_id: UUID
    meeting_id: UUID
    meeting_title: str | None = None
    meeting_started_at: datetime | None = None
    t_start: float
    t_end: float
    speaker: str | None = None
    text: str
    label: str


class ChatMessageResponse(BaseSchema):
    id: UUID
    session_id: UUID
    role: ChatRole
    text: str
    citations: list[ChatCitation] = Field(default_factory=list)
    model: str | None = None
    latency_ms: int | None = None
    created_at: datetime

    @classmethod
    def from_model(cls, message: "ChatMessage", citations: list[ChatCitation] | None = None) -> Self:
        if citations is None:
            citations = [ChatCitation.model_validate(c) for c in (message.citations or [])]
        return cls(
            id=message.id,
            session_id=message.session_id,
            role=message.role,
            text=message.text,
            citations=citations,
            model=message.model,
            latency_ms=message.latency_ms,
            created_at=message.created_at,
        )


class ChatSessionResponse(BaseSchema):
    id: UUID
    title: str
    scope: ChatScope
    meeting_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None = None
    last_message_preview: str | None = None

    @classmethod
    def from_models(cls, session: "ChatSession", last_message: "ChatMessage | None" = None) -> Self:
        return cls(
            id=session.id,
            title=session.title,
            scope=session.scope,
            meeting_id=session.meeting_id,
            created_at=session.created_at,
            updated_at=session.updated_at,
            last_message_at=last_message.created_at if last_message else None,
            last_message_preview=_preview(last_message.text) if last_message else None,
        )


class ChatSessionDetailResponse(BaseSchema):
    id: UUID
    title: str
    scope: ChatScope
    meeting_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageResponse] = Field(default_factory=list)


class ChatSessionCreateRequest(BaseSchema):
    scope: ChatScope
    meeting_id: UUID | None = None
    title: TitleStr | None = None


class ChatSessionUpdateRequest(BaseSchema):
    title: TitleStr


class ChatMessageCreateRequest(BaseSchema):
    text: NonEmptyStrippedStr


class MessageStartedEvent(BaseSchema):
    kind: Literal[ChatStreamEventKind.MESSAGE_STARTED] = ChatStreamEventKind.MESSAGE_STARTED
    user_message: ChatMessageResponse
    assistant_message_id: UUID


class TokenEvent(BaseSchema):
    kind: Literal[ChatStreamEventKind.TOKEN] = ChatStreamEventKind.TOKEN
    delta: str


class MessageCompletedEvent(BaseSchema):
    kind: Literal[ChatStreamEventKind.MESSAGE_COMPLETED] = ChatStreamEventKind.MESSAGE_COMPLETED
    message: ChatMessageResponse


class StreamErrorEvent(BaseSchema):
    kind: Literal[ChatStreamEventKind.ERROR] = ChatStreamEventKind.ERROR
    detail: str


type ChatStreamEvent = Annotated[
    MessageStartedEvent | TokenEvent | MessageCompletedEvent | StreamErrorEvent,
    Field(discriminator="kind"),
]


def _preview(text: str) -> str:
    snippet = text.splitlines()[0] if text else ""
    return snippet[:PREVIEW_MAX_LEN]
