from uuid import UUID

from app.core.base_schema import BaseSchema


class ParticipantResponse(BaseSchema):
    id: UUID
    stream_id: UUID
    name: str
    is_local_user: bool
