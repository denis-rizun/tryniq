from uuid import UUID

from app.core.base_schema import BaseSchema


class AudioTrackResponse(BaseSchema):
    stream_id: UUID
    participant_id: UUID
    participant_name: str
    is_local_user: bool
    part: int
    object_key: str
    filename: str
