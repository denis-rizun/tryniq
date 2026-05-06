from typing import Annotated

from fastapi import Depends

from app.audio.service import AudioService
from app.db import SessionDep


def get_audio_service(session: SessionDep) -> AudioService:
    return AudioService(session)


AudioServiceDep = Annotated[AudioService, Depends(get_audio_service)]
