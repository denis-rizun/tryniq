from typing import Annotated

from fastapi import Depends

from app.db import SessionDep
from app.participant.service import ParticipantService


def get_participant_service(session: SessionDep) -> ParticipantService:
    return ParticipantService(session)


ParticipantServiceDep = Annotated[ParticipantService, Depends(get_participant_service)]
