from datetime import datetime
from uuid import UUID

from app.core.base_schema import BaseSchema
from app.meeting.constants import MeetingStatus
from app.participant.schemas import ParticipantResponse


class UtteranceResponse(BaseSchema):
    id: UUID
    participant_id: UUID
    stream_id: UUID
    t_start: float
    t_end: float
    text: str
    confidence: float | None
    model: str | None
    word_timings: list | None
    is_final: bool


class TranscriptResponse(BaseSchema):
    meeting_id: UUID
    status: MeetingStatus
    participants: list[ParticipantResponse]
    utterances: list[UtteranceResponse]
    started_at: datetime
    ended_at: datetime | None
