from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, TypeAdapter

from app.asr.constants import EventKind


class _BaseEvent(BaseModel):
    model_config = {"extra": "forbid"}


class HandshakeEvent(_BaseEvent):
    kind: Literal[EventKind.HELLO] = EventKind.HELLO
    worker_id: UUID
    models: list[str] = Field(default_factory=list)
    capacity: int = 1


class Speaker(_BaseEvent):
    display_name: str | None = None
    is_local_user: bool = False


class StreamOpenEvent(_BaseEvent):
    kind: Literal[EventKind.STREAM_OPEN] = EventKind.STREAM_OPEN
    meeting_id: UUID
    stream_id: UUID
    stream_idx: int
    participant_id: UUID | None = None
    speaker: Speaker
    sample_rate: int = 16000
    encoding: Literal["pcm_s16le"] = "pcm_s16le"


class StreamCloseEvent(_BaseEvent):
    kind: Literal[EventKind.STREAM_CLOSE] = EventKind.STREAM_CLOSE
    stream_id: UUID


class PartialTranscriptEvent(_BaseEvent):
    kind: Literal[EventKind.PARTIAL] = EventKind.PARTIAL
    stream_id: UUID
    text: str
    timestamp: str | None = None


class FinalTranscriptEvent(_BaseEvent):
    kind: Literal[EventKind.FINAL] = EventKind.FINAL
    stream_id: UUID
    text: str
    t_start: float
    t_end: float
    client_utterance_id: UUID | None = None
    timestamp: str | None = None


class PingEvent(_BaseEvent):
    kind: Literal[EventKind.PING] = EventKind.PING


type ServerMessage = Annotated[
    StreamOpenEvent | StreamCloseEvent | PingEvent,
    Field(discriminator="kind"),
]
SERVER_MESSAGE_ADAPTER: TypeAdapter[ServerMessage] = TypeAdapter(ServerMessage)

type ClientMessage = Annotated[
    HandshakeEvent | PartialTranscriptEvent | FinalTranscriptEvent | PingEvent,
    Field(discriminator="kind"),
]
CLIENT_MESSAGE_ADAPTER: TypeAdapter[ClientMessage] = TypeAdapter(ClientMessage)
