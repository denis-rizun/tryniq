from fastapi import APIRouter
from starlette import status

from app.core.base_schema import ErrorResponse
from app.meeting.dependencies import MeetingDep
from app.transcript.dependencies import TranscriptServiceDep
from app.transcript.schemas import TranscriptResponse

router = APIRouter(tags=["Transcripts"])


@router.get(
    path="/meetings/{id}/transcript",
    response_model=TranscriptResponse,
    status_code=status.HTTP_200_OK,
    summary="Get meeting transcript",
    responses={404: {"model": ErrorResponse, "description": "Meeting not found"}},
)
async def get_transcript(meeting: MeetingDep, service: TranscriptServiceDep) -> TranscriptResponse:
    return await service.get_transcript(meeting)
