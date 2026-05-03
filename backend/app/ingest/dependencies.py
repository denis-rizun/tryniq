from typing import Annotated

from fastapi import Depends

from app.asr.dependencies import LiveASRClientDep
from app.db import SessionDep
from app.ingest.service import IngestService
from app.participant.service import ParticipantService


def get_participant_service(session: SessionDep) -> ParticipantService:
    return ParticipantService(session)


ParticipantServiceDep = Annotated[ParticipantService, Depends(get_participant_service)]


def get_ingest_service(
    session: SessionDep,
    participant_service: ParticipantServiceDep,
    live_asr_client: LiveASRClientDep,
) -> IngestService:
    return IngestService(session, participant_service, live_asr_client)


IngestServiceDep = Annotated[IngestService, Depends(get_ingest_service)]
