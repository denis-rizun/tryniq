from typing import Annotated

from fastapi import Depends, WebSocket

from app.db import SessionDep
from app.ingest.client import MinioClient
from app.ingest.service import IngestService
from app.participant.service import ParticipantService


def get_storage(websocket: WebSocket) -> MinioClient:
    return websocket.app.state.storage


MinioClientDep = Annotated[MinioClient, Depends(get_storage)]


def get_participant_service(session: SessionDep) -> ParticipantService:
    return ParticipantService(session)


ParticipantServiceDep = Annotated[ParticipantService, Depends(get_participant_service)]


def get_ingest_service(
    session: SessionDep,
    minio_client: MinioClientDep,
    participant_service: ParticipantServiceDep,
) -> IngestService:
    return IngestService(session, minio_client, participant_service)


IngestServiceDep = Annotated[IngestService, Depends(get_ingest_service)]
