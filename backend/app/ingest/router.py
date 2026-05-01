from uuid import UUID

from fastapi import APIRouter, WebSocket

from app.ingest.dependencies import IngestServiceDep

router = APIRouter(tags=["streams"])


@router.websocket("/meetings/{meeting_id}/streams/{stream_id}")
async def stream_audio(
    ws: WebSocket,
    meeting_id: UUID,
    stream_id: UUID,
    service: IngestServiceDep,
) -> None:
    await service.handle_stream(ws, meeting_id, stream_id)
