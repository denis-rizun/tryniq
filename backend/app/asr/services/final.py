import asyncio
from uuid import UUID

import structlog

from app.asr.clients.final import faster_whisper_client
from app.ingest.client import minio_client
from app.meeting.service import MeetingService
from app.participant.service import ParticipantService
from app.transcript.service import TranscriptService

logger = structlog.get_logger()


class FinalASRService:
    WAIT_ATTEMPTS = 30
    WAIT_DELAY_SECONDS = 1.0

    def __init__(
        self,
        participant_service: ParticipantService,
        transcript_service: TranscriptService,
        meeting_service: MeetingService,
    ) -> None:
        self.participant_service = participant_service
        self.transcript_service = transcript_service
        self.meeting_service = meeting_service

    async def run(self, meeting_id: UUID, stream_id: UUID) -> None:
        wav_bytes = await self._load_audio(meeting_id, stream_id)

        participant = await self.participant_service.get_by_stream(meeting_id, stream_id)
        if participant is None:
            logger.error("no participant row for stream", meeting_id=meeting_id, stream_id=stream_id)
            return

        if wav_bytes is None:
            await self.transcript_service.mark_no_audio(meeting_id, participant.id, stream_id)
        else:
            segments = await asyncio.to_thread(faster_whisper_client.transcribe, wav_bytes)
            logger.debug(
                "transcription complete",
                meeting_id=meeting_id,
                stream_id=stream_id,
                segment_count=len(segments),
            )
            await self.transcript_service.replace_final_for_stream(meeting_id, participant.id, stream_id, segments)

        await self.meeting_service.promote_to_final_if_complete(meeting_id)

    async def _load_audio(self, meeting_id: UUID, stream_id: UUID) -> bytes | None:
        key = minio_client.get_stream_object_key(meeting_id, stream_id)
        if not await self._wait_for_object(key):
            logger.warning(
                "no audio object after grace period",
                meeting_id=meeting_id,
                stream_id=stream_id,
                object_key=key,
            )
            return None

        return await minio_client.get_object(key)

    async def _wait_for_object(self, key: str) -> bool:
        for attempt in range(self.WAIT_ATTEMPTS):
            if await minio_client.object_exists(key):
                return True

            if attempt < self.WAIT_ATTEMPTS - 1:
                await asyncio.sleep(self.WAIT_DELAY_SECONDS)

        return False
