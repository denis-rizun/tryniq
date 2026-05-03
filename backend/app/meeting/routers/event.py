from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from starlette import status

from app.core.base_schema import ErrorResponse
from app.meeting.dependencies import GlobalLifecycleSocketDep, StreamSubscriberDep

router = APIRouter(tags=["Events"])


@router.websocket("/events/ws")
async def global_events_ws(socket: GlobalLifecycleSocketDep) -> None:
    await socket.serve()


@router.get(
    path="/meetings/{id}/events",
    status_code=status.HTTP_200_OK,
    summary="Server-sent events stream for a meeting",
    description="SSE stream of live events: meeting_lifecycle, partial_transcript, transcript_segment.",
    responses={404: {"model": ErrorResponse, "description": "Meeting not found"}},
)
async def meeting_events(subscriber: StreamSubscriberDep) -> StreamingResponse:
    return StreamingResponse(
        subscriber.stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
