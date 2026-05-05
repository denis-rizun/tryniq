from datetime import UTC, datetime
from secrets import token_urlsafe
from uuid import UUID

import structlog
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.meeting.client import redis_client
from app.meeting.constants import MEET_CODE_RE, LifecycleEvent, MeetingStatus
from app.meeting.exceptions import InvalidMeetUrlError, MeetingNotFoundError
from app.meeting.models import Meeting, MeetingRoom
from app.meeting.schemas import MeetingCreateRequest, MeetingUpdateRequest
from app.participant.models import Participant
from app.transcript.models import Utterance

logger = structlog.get_logger()


class MeetingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: MeetingCreateRequest) -> Meeting:
        room = await self.get_or_create_room(meet_url=data.meet_url, title=data.title)
        meeting = Meeting(title=data.title, room_id=room.id)
        meeting = await self._save(meeting)
        meeting.meet_code = room.meet_code
        meeting.meet_url = self.build_meet_url(room.meet_code)

        logger.debug("meeting is created", id=meeting.id, room_id=room.id)
        await redis_client.publish_meeting_lifecycle(meeting.id, LifecycleEvent.STARTED)
        return meeting

    async def retrieve(self, id: UUID) -> Meeting:
        instance = (await self.session.exec(select(Meeting).where(Meeting.id == id))).one_or_none()
        if not instance:
            raise MeetingNotFoundError()

        return instance

    async def list(self) -> list[Meeting]:
        query = select(Meeting).options(selectinload(Meeting.room)).order_by(col(Meeting.started_at).desc())
        meetings = (await self.session.exec(query)).all()
        for meeting in meetings:
            meeting.meet_code = meeting.room.meet_code
            meeting.meet_url = self.build_meet_url(meeting.room.meet_code)
        return meetings

    async def update(self, meeting: Meeting, data: MeetingUpdateRequest) -> Meeting:
        requested_final = data.status == MeetingStatus.FINAL
        update_payload = data.model_dump(exclude_none=True)

        promote_to_final = False
        if requested_final:
            meeting.ended_at = datetime.now(UTC)
            enqueued = await self._enqueue_finalization(meeting.id)
            await redis_client.publish_meeting_lifecycle(meeting.id, LifecycleEvent.ENDED)
            if enqueued:
                update_payload["status"] = MeetingStatus.FINALIZING
                await redis_client.publish_meeting_lifecycle(meeting.id, LifecycleEvent.FINALIZING)
            else:
                update_payload["status"] = MeetingStatus.FINAL
                promote_to_final = True

        for field, value in update_payload.items():
            setattr(meeting, field, value)

        meeting = await self._save(meeting)
        if promote_to_final:
            await redis_client.publish_meeting_lifecycle(meeting.id, LifecycleEvent.FINAL)

        room = (await self.session.exec(select(MeetingRoom).where(MeetingRoom.id == meeting.room_id))).one()
        logger.debug("meeting is updated", id=meeting.id, status=meeting.status)
        meeting.meet_code = room.meet_code
        meeting.meet_url = self.build_meet_url(room.meet_code)
        return meeting

    async def promote_to_final_if_complete(self, meeting_id: UUID) -> bool:
        meeting = await self._get_finalizing(meeting_id)
        if not meeting:
            return False

        if not await self._all_streams_completed(meeting_id):
            return False

        meeting.status = MeetingStatus.FINAL
        if meeting.ended_at is None:
            meeting.ended_at = datetime.now(UTC)

        await self._save(meeting)
        logger.info("meeting promoted to final", meeting_id=meeting_id)
        await redis_client.publish_meeting_lifecycle(meeting.id, LifecycleEvent.FINAL)
        await self.enqueue_graph_build(meeting_id)
        await self.enqueue_utterance_embeddings(meeting_id)
        await self.enqueue_metadata_extraction(meeting_id)
        return True

    @staticmethod
    async def enqueue_graph_build(meeting_id: UUID) -> None:
        from app.graph.tasks import build_graph

        await build_graph.kiq(str(meeting_id), None, None)
        logger.debug("enqueued build_graph", meeting_id=meeting_id)

    @staticmethod
    async def enqueue_utterance_embeddings(meeting_id: UUID) -> None:
        from app.chat.tasks import embed_utterances

        await embed_utterances.kiq(str(meeting_id))
        logger.debug("enqueued embed_utterances", meeting_id=meeting_id)

    @staticmethod
    async def enqueue_metadata_extraction(meeting_id: UUID) -> None:
        from app.metadata.tasks import extract_meeting_metadata

        await extract_meeting_metadata.kiq(str(meeting_id))
        logger.debug("enqueued extract_meeting_metadata", meeting_id=meeting_id)

    async def create_for_upload(self, title: str) -> Meeting:
        code = f"upl-{token_urlsafe(8).lower()}"
        room = MeetingRoom(meet_code=code, title=title)
        self.session.add(room)
        await self.session.flush()
        meeting = Meeting(title=title, room_id=room.id, status=MeetingStatus.UPLOADING)
        self.session.add(meeting)
        await self.session.commit()
        await self.session.refresh(meeting)
        meeting.meet_code = room.meet_code
        meeting.meet_url = self.build_meet_url(room.meet_code)

        logger.debug("upload meeting created", id=meeting.id, room_id=room.id)
        await redis_client.publish_meeting_lifecycle(meeting.id, LifecycleEvent.STARTED)
        await redis_client.publish_meeting_lifecycle(meeting.id, LifecycleEvent.UPLOADING)
        return meeting

    async def set_status(self, meeting_id: UUID, status: MeetingStatus) -> None:
        meeting = await self.retrieve(meeting_id)
        meeting.status = status
        if status == MeetingStatus.FINAL and meeting.ended_at is None:
            meeting.ended_at = datetime.now(UTC)
        await self._save(meeting)

    async def _get_finalizing(self, meeting_id: UUID) -> Meeting | None:
        meeting = (await self.session.exec(select(Meeting).where(Meeting.id == meeting_id))).one_or_none()
        if not meeting or meeting.status != MeetingStatus.FINALIZING:
            return None

        return meeting

    async def _all_streams_completed(self, meeting_id: UUID) -> bool:
        total_query = select(func.count(Participant.id)).where(Participant.meeting_id == meeting_id)
        total = (await self.session.exec(total_query)).one()

        completed_query = select(func.count(func.distinct(Utterance.stream_id))).where(
            Utterance.meeting_id == meeting_id
        )
        completed = (await self.session.exec(completed_query)).one()
        return 0 < total <= completed

    async def _enqueue_finalization(self, meeting_id: UUID) -> bool:
        from app.asr.tasks import transcribe_final

        query = select(Participant).where(Participant.meeting_id == meeting_id)
        participants = (await self.session.exec(query)).all()

        if not participants:
            logger.warning("finalize requested but no participants", meeting_id=meeting_id)
            return False

        for p in participants:
            await transcribe_final.kiq(str(meeting_id), str(p.stream_id))
            logger.debug(
                "enqueued transcribe_final",
                meeting_id=meeting_id,
                stream_id=p.stream_id,
                speaker=p.name,
            )
        return True

    async def _save(self, instance: Meeting) -> Meeting:
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def get_or_create_room(self, meet_url: str, title: str) -> MeetingRoom:
        code = self.extract_meet_code(meet_url)
        stmt = (
            pg_insert(MeetingRoom)
            .values(meet_code=code, title=title)
            .on_conflict_do_nothing(index_elements=["meet_code"])
        )
        await self.session.exec(stmt)
        room = (await self.session.exec(select(MeetingRoom).where(MeetingRoom.meet_code == code))).one()
        return room

    @staticmethod
    def extract_meet_code(meet_url: str) -> str:
        match = MEET_CODE_RE.search(meet_url.lower())
        if not match:
            raise InvalidMeetUrlError()

        return match.group(1)

    @staticmethod
    def build_meet_url(meet_code: str) -> str:
        return f"https://meet.google.com/{meet_code}"
