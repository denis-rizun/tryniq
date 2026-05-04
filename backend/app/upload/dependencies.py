from typing import Annotated

from fastapi import Depends

from app.db import SessionDep
from app.meeting.dependencies import MeetingServiceDep
from app.participant.service import ParticipantService
from app.transcript.service import TranscriptService
from app.upload.service import UploadService


def get_upload_service(meeting_service: MeetingServiceDep, session: SessionDep) -> UploadService:
    return UploadService(meeting_service, ParticipantService(session), TranscriptService(session))


UploadServiceDep = Annotated[UploadService, Depends(get_upload_service)]
