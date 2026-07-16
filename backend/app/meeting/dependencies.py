from typing import Annotated
from uuid import UUID

from fastapi import Depends
from starlette.websockets import WebSocket

from app.db import SessionDep
from app.meeting.models import Meeting
from app.meeting.services.lifecycle_socket import GlobalLifecycleSocket
from app.meeting.services.meeting import MeetingService
from app.meeting.services.stream_subscriber import StreamSubscriber


def get_meeting_service(session: SessionDep) -> MeetingService:
    return MeetingService(session)


MeetingServiceDep = Annotated[MeetingService, Depends(get_meeting_service)]


async def get_meeting(id: UUID, service: MeetingServiceDep) -> Meeting:
    return await service.retrieve(id)


MeetingDep = Annotated[Meeting, Depends(get_meeting)]


def get_stream_subscriber(meeting: MeetingDep) -> StreamSubscriber:
    return StreamSubscriber(meeting.id)


StreamSubscriberDep = Annotated[StreamSubscriber, Depends(get_stream_subscriber)]


def get_global_lifecycle_socket(ws: WebSocket) -> GlobalLifecycleSocket:
    return GlobalLifecycleSocket(ws)


GlobalLifecycleSocketDep = Annotated[GlobalLifecycleSocket, Depends(get_global_lifecycle_socket)]
