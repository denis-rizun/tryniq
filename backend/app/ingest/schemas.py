from typing import Literal
from uuid import UUID

from pydantic import Field, TypeAdapter

from app.core.base_schema import BaseSchema


class Speaker(BaseSchema):
    tile_id: str | None = None
    display_name: str = ""
    is_local_user: bool = False


class AudioFormat(BaseSchema):
    sample_rate: Literal[16000]
    encoding: Literal["pcm_s16le"]
    channels: Literal[1]


class StreamInitMessage(BaseSchema):
    type: Literal["init"]
    meeting_id: UUID
    stream_id: UUID
    speaker: Speaker
    audio_format: AudioFormat
    client_started_at: str | None = None
    client_version: str | None = None


class VoiceActivityStartedMessage(BaseSchema):
    type: Literal["vad_speech_start"]
    timestamp_seconds: float = Field(alias="t")


class VoiceActivityEndedMessage(BaseSchema):
    type: Literal["vad_speech_end"]
    timestamp_seconds: float = Field(alias="t")


class SpeakerActiveMessage(BaseSchema):
    type: Literal["speaker_active"]
    active: bool
    timestamp_seconds: float = Field(alias="t")


class SpeakerRenamedMessage(BaseSchema):
    type: Literal["speaker_renamed"]
    new_name: str


class StreamEndedMessage(BaseSchema):
    type: Literal["stream_end"]


class StreamDiscardedMessage(BaseSchema):
    type: Literal["discard"]
    reason: str | None = None


ControlMessage = (
    VoiceActivityStartedMessage
    | VoiceActivityEndedMessage
    | SpeakerActiveMessage
    | SpeakerRenamedMessage
    | StreamEndedMessage
    | StreamDiscardedMessage
)

CONTROL_ADAPTER: TypeAdapter[ControlMessage] = TypeAdapter(ControlMessage)
