import asyncio
from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import delete, func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.asr.constants import NO_AUDIO_MARKER, NO_SPEECH_SUFFIX, WAIT_ATTEMPTS, WAIT_DELAY_SECONDS
from app.asr.model_handler import get_asr_model
from app.asr.types import AsrSegment
from app.db import async_session
from app.ingest.client import MinioClient
from app.meeting.constants import MeetingStatus
from app.meeting.models import Meeting
from app.participant.models import Participant
from app.transcript.models import Utterance

logger = structlog.get_logger()


class ASRService:
    def __init__(self, storage: MinioClient | None = None) -> None:
        self._storage = storage or MinioClient()

    async def run(self, meeting_id: UUID, stream_id: UUID) -> None:
        wav_bytes = await self._load_audio(meeting_id, stream_id)
        if wav_bytes is None:
            await self._mark_no_audio(meeting_id, stream_id)
            await self._promote_meeting_if_done(meeting_id)
            return

        provider = get_asr_model()

        segments = await asyncio.to_thread(provider.transcribe, wav_bytes)
        logger.info(
            "asr: transcription complete",
            meeting_id=meeting_id,
            stream_id=stream_id,
            segment_count=len(segments),
        )
        await self._persist_utterances(meeting_id, stream_id, segments, provider.model_name)
        await self._promote_meeting_if_done(meeting_id)

    async def _load_audio(self, meeting_id: UUID, stream_id: UUID) -> bytes | None:
        key = self._storage.get_stream_object_key(meeting_id, stream_id)
        if not await self._wait_for_object(key):
            logger.warning(
                "asr: no audio object after grace period",
                meeting_id=meeting_id,
                stream_id=stream_id,
                object_key=key,
            )
            return None

        return await self._storage.get_object(key)

    async def _wait_for_object(self, key: str) -> bool:
        for attempt in range(WAIT_ATTEMPTS):
            if await self._storage.object_exists(key):
                return True

            if attempt < WAIT_ATTEMPTS - 1:
                await asyncio.sleep(WAIT_DELAY_SECONDS)

        return False

    async def _persist_utterances(
        self,
        meeting_id: UUID,
        stream_id: UUID,
        segments: list[AsrSegment],
        model_name: str,
    ) -> None:
        async with async_session() as session:
            participant = await self._get_participant(session, meeting_id, stream_id)
            if not participant:
                logger.error("asr: no participant row for stream", meeting_id=meeting_id, stream_id=stream_id)
                return

            await self._delete_utterances_for_stream(session, meeting_id, stream_id)
            for row in self._build_utterance_rows(meeting_id, participant.id, stream_id, segments, model_name):
                session.add(row)

            await session.commit()

    async def _mark_no_audio(self, meeting_id: UUID, stream_id: UUID) -> None:
        async with async_session() as session:
            participant = await self._get_participant(session, meeting_id, stream_id)
            if not participant:
                return

            await self._delete_utterances_for_stream(session, meeting_id, stream_id)
            session.add(self._sentinel_utterance(meeting_id, participant.id, stream_id, NO_AUDIO_MARKER))
            await session.commit()

    async def _promote_meeting_if_done(self, meeting_id: UUID) -> None:
        async with async_session() as session:
            meeting = await self._get_finalizing_meeting(session, meeting_id)
            if not meeting:
                return

            if not await self._all_streams_completed(session, meeting_id):
                return

            meeting.status = MeetingStatus.FINAL
            if meeting.ended_at is None:
                meeting.ended_at = datetime.now(UTC)

            session.add(meeting)
            await session.commit()
            logger.info("asr: meeting promoted to final", meeting_id=meeting_id)

    def _build_utterance_rows(
        self,
        meeting_id: UUID,
        participant_id: UUID,
        stream_id: UUID,
        segments: list[AsrSegment],
        model_name: str,
    ) -> list[Utterance]:
        if not segments:
            model = f"{model_name}{NO_SPEECH_SUFFIX}"
            return [self._sentinel_utterance(meeting_id, participant_id, stream_id, model)]
        return [self._segment_utterance(meeting_id, participant_id, stream_id, seg, model_name) for seg in segments]

    @staticmethod
    async def _get_participant(session: AsyncSession, meeting_id: UUID, stream_id: UUID) -> Participant | None:
        query = (
            select(Participant).where(Participant.meeting_id == meeting_id).where(Participant.stream_id == stream_id)
        )
        return (await session.exec(query)).one_or_none()

    @staticmethod
    async def _delete_utterances_for_stream(session: AsyncSession, meeting_id: UUID, stream_id: UUID) -> None:
        await session.exec(
            delete(Utterance).where(Utterance.meeting_id == meeting_id).where(Utterance.stream_id == stream_id)
        )

    @staticmethod
    async def _get_finalizing_meeting(session: AsyncSession, meeting_id: UUID) -> Meeting | None:
        meeting = (await session.exec(select(Meeting).where(Meeting.id == meeting_id))).one_or_none()
        if not meeting or meeting.status != MeetingStatus.FINALIZING:
            return None

        return meeting

    @staticmethod
    async def _all_streams_completed(session: AsyncSession, meeting_id: UUID) -> bool:
        get_total_participant_query = select(func.count(Participant.id)).where(Participant.meeting_id == meeting_id)
        total = (await session.exec(get_total_participant_query)).one()

        get_completed_utterance_query = select(func.count(func.distinct(Utterance.stream_id))).where(
            Utterance.meeting_id == meeting_id
        )
        completed = (await session.exec(get_completed_utterance_query)).one()
        return 0 < total <= completed

    @staticmethod
    def _segment_utterance(
        meeting_id: UUID,
        participant_id: UUID,
        stream_id: UUID,
        seg: AsrSegment,
        model_name: str,
    ) -> Utterance:
        return Utterance(
            meeting_id=meeting_id,
            participant_id=participant_id,
            stream_id=stream_id,
            t_start=seg.t_start,
            t_end=seg.t_end,
            text=seg.text,
            confidence=seg.confidence,
            model=model_name,
            word_timings=seg.words_as_jsonable() if seg.words else None,
            is_final=True,
        )

    @staticmethod
    def _sentinel_utterance(
        meeting_id: UUID,
        participant_id: UUID,
        stream_id: UUID,
        model: str,
    ) -> Utterance:
        return Utterance(
            meeting_id=meeting_id,
            participant_id=participant_id,
            stream_id=stream_id,
            t_start=0.0,
            t_end=0.0,
            text="",
            confidence=None,
            model=model,
            word_timings=None,
            is_final=True,
        )
