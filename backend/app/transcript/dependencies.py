from typing import Annotated

from fastapi import Depends

from app.db import SessionDep
from app.transcript.service import TranscriptService


def get_transcript_service(session: SessionDep) -> TranscriptService:
    return TranscriptService(session)


TranscriptServiceDep = Annotated[TranscriptService, Depends(get_transcript_service)]
