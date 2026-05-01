from datetime import datetime
from uuid import UUID

from app.core.base_schema import BaseSchema
from app.meeting.constants import MeetingStatus


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


class MeetingUpdateRequest(BaseSchema):
    status: MeetingStatus
