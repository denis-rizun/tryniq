from uuid import UUID

from app.core.base_schema import BaseSchema


class UploadResponse(BaseSchema):
    meeting_id: UUID
