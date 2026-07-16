from uuid import UUID

import structlog
from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.ingest.constants import UNRESOLVED_NAME_RE
from app.meeting.models import Meeting
from app.participant.exceptions import ParticipantNameUnresolvedError
from app.participant.models import Participant
from app.participant.schemas import PersonListItem, PersonUtteranceItem
from app.transcript.models import Utterance

logger = structlog.get_logger()


class ParticipantService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        meeting_id: UUID,
        stream_id: UUID,
        display_name: str,
        is_local_user: bool,
    ) -> Participant:
        resolved_name = self.resolve_name(display_name)
        if not resolved_name:
            raise ParticipantNameUnresolvedError()

        query = (
            select(Participant).where(Participant.meeting_id == meeting_id).where(Participant.stream_id == stream_id)
        )
        found = (await self.session.exec(query)).one_or_none()

        if found:
            return await self.update(found, resolved_name)

        participant = Participant(
            meeting_id=meeting_id,
            stream_id=stream_id,
            name=resolved_name,
            is_local_user=is_local_user,
        )
        await self._save(participant)
        logger.debug("participant is created", id=participant.id)
        return participant

    async def create_for_upload(
        self,
        meeting_id: UUID,
        stream_id: UUID,
        label: str,
    ) -> Participant:
        participant = Participant(
            meeting_id=meeting_id,
            stream_id=stream_id,
            name=label,
            is_local_user=False,
        )
        await self._save(participant)
        logger.debug("upload participant created", id=participant.id, label=label)
        return participant

    async def list_participants(self, meeting: Meeting) -> list[Participant]:
        query = select(Participant).where(Participant.meeting_id == meeting.id)
        result = await self.session.exec(query)
        return list(result.all())

    async def list_people(self) -> list[PersonListItem]:
        query = (
            select(
                Participant.name,
                func.bool_or(Participant.is_local_user).label("is_local_user"),
                func.count(func.distinct(Participant.meeting_id)).label("meeting_count"),
                func.max(Meeting.started_at).label("last_meeting_at"),
                func.array_agg(Participant.id).label("participant_ids"),
            )
            .join(Meeting, Meeting.id == Participant.meeting_id)
            .group_by(Participant.name)
            .order_by(func.max(Meeting.started_at).desc())
        )
        rows = (await self.session.exec(query)).all()
        return [
            PersonListItem(
                name=row.name,
                is_local_user=bool(row.is_local_user),
                meeting_count=int(row.meeting_count),
                last_meeting_at=row.last_meeting_at,
                participant_ids=list(row.participant_ids),
            )
            for row in rows
        ]

    async def list_person_utterances(self, name: str, limit: int = 6) -> list[PersonUtteranceItem]:
        query = (
            select(Utterance, Meeting.title)
            .join(Participant, Participant.id == Utterance.participant_id)
            .join(Meeting, Meeting.id == Utterance.meeting_id)
            .where(Participant.name == name)
            .where(col(Utterance.is_final).is_(True))
            .where(Utterance.text != "")
            .order_by(Meeting.started_at.desc(), Utterance.t_start.desc())  # type: ignore[attr-defined]
            .limit(limit)
        )
        rows = (await self.session.exec(query)).all()
        return [
            PersonUtteranceItem(
                id=utt.id,
                meeting_id=utt.meeting_id,
                meeting_title=meeting_title,
                t_start=utt.t_start,
                text=utt.text,
            )
            for utt, meeting_title in rows
        ]

    async def get_by_stream(self, meeting_id: UUID, stream_id: UUID) -> Participant | None:
        query = (
            select(Participant).where(Participant.meeting_id == meeting_id).where(Participant.stream_id == stream_id)
        )
        return (await self.session.exec(query)).one_or_none()

    async def update(self, instance: Participant, name: str) -> Participant:
        if instance.name != name:
            instance.name = name
            await self._save(instance)
            logger.debug("participant is updated", id=instance.id)

        return instance

    @staticmethod
    def resolve_name(display_name: str) -> str | None:
        name = display_name.strip()
        is_unresolved = bool(UNRESOLVED_NAME_RE.match(name)) if name else False
        return None if is_unresolved else name

    async def _save(self, instance: Participant) -> Participant:
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance
