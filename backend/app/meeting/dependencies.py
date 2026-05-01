from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.db import SessionDep
from app.meeting.models import Meeting
from app.meeting.service import MeetingService


def get_meeting_service(session: SessionDep) -> MeetingService:
    return MeetingService(session)


MeetingServiceDep = Annotated[MeetingService, Depends(get_meeting_service)]


async def get_meeting(id: UUID, service: MeetingServiceDep) -> Meeting:
    return await service.retrieve(id)


MeetingDep = Annotated[Meeting, Depends(get_meeting)]
