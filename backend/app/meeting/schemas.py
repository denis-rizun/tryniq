from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from app.core.base_schema import BaseSchema, UpdateSchema
from app.meeting.constants import LifecycleEvent, MeetingEventKind, MeetingStatus


class MeetingCreateRequest(BaseSchema):
    title: str
    meet_url: str


class MeetingResponse(BaseSchema):
    id: UUID
    title: str
    meet_url: str
    meet_code: str
    room_id: UUID
    status: MeetingStatus
    started_at: datetime
    ended_at: datetime | None
    summary: str | None = None
    metadata_generated_at: datetime | None = None
    participants_count: int = 0
    decisions_count: int = 0
    open_questions_count: int = 0
    topics_count: int = 0


class MeetingUpdateRequest(UpdateSchema):
    status: MeetingStatus | None = None
    title: str | None = None


class MeetingLifecycleEvent(BaseSchema):
    kind: Literal[MeetingEventKind.MEETING_LIFECYCLE] = MeetingEventKind.MEETING_LIFECYCLE
    meeting_id: UUID
    event: LifecycleEvent
    timestamp: datetime


class PartialTranscriptEvent(BaseSchema):
    kind: Literal[MeetingEventKind.PARTIAL_TRANSCRIPT] = MeetingEventKind.PARTIAL_TRANSCRIPT
    meeting_id: UUID
    stream_id: UUID
    participant_id: UUID | None
    text: str
    timestamp: datetime


class TranscriptSegmentEvent(BaseSchema):
    kind: Literal[MeetingEventKind.TRANSCRIPT_SEGMENT] = MeetingEventKind.TRANSCRIPT_SEGMENT
    meeting_id: UUID
    stream_id: UUID
    participant_id: UUID | None
    utterance_id: UUID
    text: str
    t_start: float
    t_end: float
    is_final: bool
    timestamp: datetime


type MeetingEvent = Annotated[
    MeetingLifecycleEvent | PartialTranscriptEvent | TranscriptSegmentEvent,
    Field(discriminator="kind"),
]
