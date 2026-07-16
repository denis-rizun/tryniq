from uuid import UUID

import structlog
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.meeting.client import redis_client
from app.meeting.constants import LifecycleEvent
from app.meeting.models import Meeting
from app.metadata.schemas import MeetingMetadataResponse
from app.metadata.services.extractor import MetadataExtractor
from app.metadata.services.reader import MetadataReader
from app.metadata.services.references import MetadataReferences
from app.metadata.services.related_finder import RelatedMeetingsFinder
from app.metadata.services.writer import MetadataGraphWriter
from app.participant.models import Participant
from app.transcript.models import Utterance

logger = structlog.get_logger()


class MetadataService:
    def __init__(
        self,
        session: AsyncSession,
        extractor: MetadataExtractor,
        writer: MetadataGraphWriter,
        related_finder: RelatedMeetingsFinder,
        reader: MetadataReader,
    ) -> None:
        self.session = session
        self.extractor = extractor
        self.writer = writer
        self.related_finder = related_finder
        self.reader = reader

    async def extract_metadata(self, meeting_id: UUID) -> None:
        meeting = (await self.session.exec(select(Meeting).where(Meeting.id == meeting_id))).one_or_none()
        if not meeting:
            logger.warning("Meeting was not found for metadata extraction", meeting_id=str(meeting_id))
            return

        utterances = await self._load_utterances(meeting_id)
        if not utterances:
            logger.info("Skipping metadata extraction without utterances", meeting_id=str(meeting_id))
            return

        participants = await self._load_participants(meeting_id)
        references = MetadataReferences(utterances, participants)
        metadata = await self.extractor.extract(references)

        await self.writer.reset_generated(meeting_id)
        person_ref_to_node = await self.writer.ensure_persons(meeting_id, participants)

        if metadata:
            await self.writer.write_metadata(meeting_id, metadata, references, person_ref_to_node)

        summary = metadata.summary if metadata else None
        await self.writer.persist_summary(meeting, summary)

        if metadata and metadata.topics:
            ranked = await self.related_finder.rank(meeting_id, meeting)
            await self.writer.link_related_meetings(meeting_id, ranked)

        await self.session.commit()
        await redis_client.publish_meeting_lifecycle(meeting_id, LifecycleEvent.METADATA_READY)
        logger.info(
            "Meeting metadata extraction finished",
            meeting_id=str(meeting_id),
            have_metadata=metadata is not None,
        )

    async def get_meeting_metadata(self, meeting_id: UUID) -> MeetingMetadataResponse:
        return await self.reader.read(meeting_id)

    async def _load_utterances(self, meeting_id: UUID) -> list[Utterance]:
        query = (
            select(Utterance)
            .where(Utterance.meeting_id == meeting_id)
            .where(Utterance.text != "")
            .where(col(Utterance.is_final).is_(True))
            .order_by(Utterance.t_start)
        )
        return list((await self.session.exec(query)).all())

    async def _load_participants(self, meeting_id: UUID) -> list[Participant]:
        query = select(Participant).where(Participant.meeting_id == meeting_id)
        return list((await self.session.exec(query)).all())
