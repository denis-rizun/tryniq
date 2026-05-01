from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.meeting.models import Meeting
from app.participant.models import Participant
from app.participant.schemas import ParticipantResponse
from app.transcript.models import Utterance
from app.transcript.schemas import TranscriptResponse, UtteranceResponse


class TranscriptService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

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
