from uuid import UUID

from sqlalchemy import delete
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.asr.clients.final import ASRSegment
from app.config import config
from app.meeting.models import Meeting
from app.participant.models import Participant
from app.participant.schemas import ParticipantResponse
from app.transcript.models import Utterance
from app.transcript.schemas import TranscriptResponse, UtteranceResponse


class TranscriptService:
    NO_AUDIO_MARKER = "no-audio"
    NO_SPEECH_SUFFIX = ":no-speech"

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_live(
        self,
        meeting_id: UUID,
        participant_id: UUID,
        stream_id: UUID,
        text: str,
        t_start: float,
        t_end: float,
    ) -> Utterance | None:
        if await self._is_contained_by_existing_live(stream_id, t_start, t_end):
            return None

        await self._delete_contained_live(stream_id, t_start, t_end)

        row = Utterance(
            meeting_id=meeting_id,
            participant_id=participant_id,
            stream_id=stream_id,
            t_start=t_start,
            t_end=t_end,
            text=text,
            confidence=None,
            model=config.asr.live_asr_id,
            word_timings=None,
            is_final=False,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def _is_contained_by_existing_live(self, stream_id: UUID, t_start: float, t_end: float) -> bool:
        query = (
            select(Utterance.id)
            .where(col(Utterance.stream_id) == stream_id)
            .where(col(Utterance.is_final).is_(False))
            .where(col(Utterance.t_start) <= t_start)
            .where(col(Utterance.t_end) >= t_end)
            .limit(1)
        )
        result = await self.session.exec(query)
        return result.one_or_none() is not None

    async def _delete_contained_live(self, stream_id: UUID, t_start: float, t_end: float) -> None:
        await self.session.exec(
            delete(Utterance)
            .where(col(Utterance.stream_id) == stream_id)
            .where(col(Utterance.is_final).is_(False))
            .where(col(Utterance.t_start) >= t_start)
            .where(col(Utterance.t_end) <= t_end)
        )

    async def replace_final_for_stream(
        self,
        meeting_id: UUID,
        participant_id: UUID,
        stream_id: UUID,
        segments: list[ASRSegment],
    ) -> None:
        await self._clear_for_stream(meeting_id, stream_id)
        rows = self._build_final_rows(meeting_id, participant_id, stream_id, segments)
        for row in rows:
            self.session.add(row)
        await self.session.commit()

    async def mark_no_audio(self, meeting_id: UUID, participant_id: UUID, stream_id: UUID) -> None:
        await self._clear_for_stream(meeting_id, stream_id)
        self.session.add(self._sentinel_utterance(meeting_id, participant_id, stream_id, self.NO_AUDIO_MARKER))
        await self.session.commit()

    async def get_transcript(self, meeting: Meeting) -> TranscriptResponse:
        users = (await self.session.exec(select(Participant).where(Participant.meeting_id == meeting.id))).all()

        query = (
            select(Utterance)
            .where(Utterance.meeting_id == meeting.id)
            .where(Utterance.text != "")
            .order_by(Utterance.t_start)
        )
        utterances = (await self.session.exec(query)).all()
        return TranscriptResponse(
            meeting_id=meeting.id,
            status=meeting.status,
            started_at=meeting.started_at,
            ended_at=meeting.ended_at,
            participants=[ParticipantResponse.model_validate(p) for p in users],
            utterances=[UtteranceResponse.model_validate(u) for u in utterances],
        )

    async def _clear_for_stream(self, meeting_id: UUID, stream_id: UUID) -> None:
        await self.session.exec(
            delete(Utterance).where(Utterance.meeting_id == meeting_id).where(Utterance.stream_id == stream_id)
        )

    def _build_final_rows(
        self,
        meeting_id: UUID,
        participant_id: UUID,
        stream_id: UUID,
        segments: list[ASRSegment],
    ) -> list[Utterance]:
        if not segments:
            model = f"{config.asr.final_asr_id}{self.NO_SPEECH_SUFFIX}"
            return [self._sentinel_utterance(meeting_id, participant_id, stream_id, model)]

        return [self._segment_utterance(meeting_id, participant_id, stream_id, seg) for seg in segments]

    @staticmethod
    def _segment_utterance(
        meeting_id: UUID,
        participant_id: UUID,
        stream_id: UUID,
        seg: ASRSegment,
    ) -> Utterance:
        return Utterance(
            meeting_id=meeting_id,
            participant_id=participant_id,
            stream_id=stream_id,
            t_start=seg.t_start,
            t_end=seg.t_end,
            text=seg.text,
            confidence=seg.confidence,
            model=config.asr.final_asr_id,
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
