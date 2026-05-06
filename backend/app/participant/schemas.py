from datetime import datetime
from uuid import UUID

from app.core.base_schema import BaseSchema


class ParticipantResponse(BaseSchema):
    id: UUID
    stream_id: UUID
    name: str
    is_local_user: bool


class PersonListItem(BaseSchema):
    name: str
    is_local_user: bool
    meeting_count: int
    last_meeting_at: datetime | None
    participant_ids: list[UUID]


class PersonUtteranceItem(BaseSchema):
    id: UUID
    meeting_id: UUID
    meeting_title: str
    t_start: float
    text: str
