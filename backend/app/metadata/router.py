from fastapi import APIRouter
from starlette import status

from app.core.base_schema import ErrorResponse
from app.meeting.dependencies import MeetingDep
from app.metadata.dependencies import MetadataServiceDep
from app.metadata.schemas import MeetingMetadataResponse

router = APIRouter(prefix="/meetings", tags=["metadata"])


@router.get(
    path="/{id}/metadata",
    response_model=MeetingMetadataResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Meeting Metadata",
    description="Return summary, decisions, action items, open questions, topics, and related past meetings.",
    responses={
        404: {"model": ErrorResponse, "description": "Meeting not found"},
    },
)
async def get_meeting_metadata(meeting: MeetingDep, service: MetadataServiceDep) -> MeetingMetadataResponse:
    return await service.get_meeting_metadata(meeting.id)
