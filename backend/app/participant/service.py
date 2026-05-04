from uuid import UUID

import structlog
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.ingest.constants import UNRESOLVED_NAME_RE
from app.meeting.models import Meeting
from app.participant.exceptions import ParticipantNameUnresolvedError
from app.participant.models import Participant

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

    async def list(self, meeting: Meeting) -> list[Participant]:
        query = select(Participant).where(Participant.meeting_id == meeting.id)
        result = await self.session.exec(query)
        return list(result.all())

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
