from uuid import UUID

import structlog
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.ingest.constants import UNRESOLVED_NAME_RE
from app.participant.exceptions import ParticipantNameUnresolvedError
from app.participant.models import Participant

logger = structlog.get_logger()


class ParticipantService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
        found = (await self._session.exec(query)).one_or_none()

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
        self._session.add(instance)
        await self._session.commit()
        await self._session.refresh(instance)
        return instance
