from typing import Annotated

from fastapi import Depends, WebSocket

from app.db import SessionDep
from app.ingest.client import MinioClient
from app.ingest.service import IngestService


def get_storage(websocket: WebSocket) -> MinioClient:
    return websocket.app.state.storage


MinioClientDep = Annotated[MinioClient, Depends(get_storage)]


def get_ingest_service(session: SessionDep, minio_client: MinioClientDep) -> IngestService:
    return IngestService(session, minio_client)


IngestServiceDep = Annotated[IngestService, Depends(get_ingest_service)]
