from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.meeting.constants import MEET_CODE_RE, MeetingStatus
from app.meeting.exceptions import InvalidMeetUrlError, MeetingNotFoundError
from app.meeting.models import Meeting, MeetingRoom
from app.meeting.schemas import MeetingCreateRequest, MeetingResponse, MeetingUpdateRequest

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
        return meeting

    async def retrieve(self, id: UUID) -> Meeting:
        instance = (await self.session.exec(select(Meeting).where(Meeting.id == id))).one_or_none()
        if not instance:
            raise MeetingNotFoundError()

        return instance

    async def update(self, meeting: Meeting, data: MeetingUpdateRequest) -> Meeting:
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(meeting, field, value)

        if data.status == MeetingStatus.FINAL:
            meeting.ended_at = datetime.now(UTC)

        meeting = await self._save(meeting)
        room = (await self.session.exec(select(MeetingRoom).where(MeetingRoom.id == meeting.room_id))).one()
        logger.debug("meeting is updated", id=meeting.id)
        meeting.meet_code = room.meet_code
        meeting.meet_url = self.build_meet_url(room.meet_code)
        return meeting

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
