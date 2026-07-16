from uuid import UUID

from app.db import async_session
from app.meeting.services.meeting import MeetingService
from app.participant.service import ParticipantService
from app.tasks import broker
from app.transcript.service import TranscriptService
from app.upload.service import UploadService


@broker.task(retry_on_error=True, max_retries=2)
async def process_upload(meeting_id: str, source_key: str) -> None:
    async with async_session() as session:
        service = UploadService(
            MeetingService(session),
            ParticipantService(session),
            TranscriptService(session),
        )
        await service.process(UUID(meeting_id), source_key)
