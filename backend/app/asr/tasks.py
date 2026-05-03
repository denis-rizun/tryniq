from uuid import UUID

from app.asr.services.final import FinalASRService
from app.db import async_session
from app.meeting.service import MeetingService
from app.participant.service import ParticipantService
from app.tasks import broker
from app.transcript.service import TranscriptService


@broker.task(retry_on_error=True, max_retries=2)
async def transcribe_final(meeting_id: str, stream_id: str) -> None:
    async with async_session() as session:
        service = FinalASRService(
            ParticipantService(session),
            TranscriptService(session),
            MeetingService(session),
        )
        await service.run(UUID(meeting_id), UUID(stream_id))
