from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import Response
from starlette import status

from app.audio.dependencies import AudioServiceDep
from app.audio.schemas import AudioTrackResponse
from app.core.base_schema import ErrorResponse
from app.meeting.dependencies import MeetingDep

router = APIRouter(prefix="/meetings", tags=["audio"])


@router.get(
    path="/{id}/audio",
    response_model=list[AudioTrackResponse],
    status_code=status.HTTP_200_OK,
    summary="List meeting audio tracks",
    description="List per-speaker audio tracks available for download.",
    responses={404: {"model": ErrorResponse, "description": "Meeting not found"}},
)
async def list_audio_tracks(meeting: MeetingDep, service: AudioServiceDep) -> list[AudioTrackResponse]:
    return await service.list_tracks(meeting.id)


@router.get(
    path="/{id}/audio/{stream_id}",
    status_code=status.HTTP_200_OK,
    summary="Download meeting audio track",
    description="Download a single per-speaker WAV file.",
    responses={
        200: {"content": {"audio/wav": {}}},
        404: {"model": ErrorResponse, "description": "Audio track not found"},
    },
)
async def download_audio_track(
    meeting: MeetingDep,
    stream_id: UUID,
    service: AudioServiceDep,
    part: int = 1,
) -> Response:
    body, filename = await service.get_track(meeting.id, stream_id, part)
    return Response(
        content=body,
        media_type="audio/wav",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
