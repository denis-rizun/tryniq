from fastapi import APIRouter
from starlette import status

from app.core.base_schema import ErrorResponse
from app.meeting.dependencies import MeetingDep, MeetingServiceDep
from app.meeting.schemas import MeetingCreateRequest, MeetingResponse, MeetingUpdateRequest

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.post(
    path="",
    response_model=MeetingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Meeting",
    description="Create a new meeting.",
    responses={
        404: {"model": ErrorResponse, "description": "Meeting not found"},
    },
)
async def create_meeting(body: MeetingCreateRequest, service: MeetingServiceDep) -> MeetingResponse:
    instance = await service.create(body)
    return MeetingResponse.model_validate(instance)


@router.get(
    path="",
    response_model=list[MeetingResponse],
    status_code=status.HTTP_200_OK,
    summary="List meetings",
    description="List all meetings.",
)
async def list_meetings(service: MeetingServiceDep) -> list[MeetingResponse]:
    result = await service.list()
    return [MeetingResponse.model_validate(model) for model in result]


@router.patch(
    path="/{id}",
    response_model=MeetingResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Meeting",
    description="Update meeting status.",
    responses={
        404: {"model": ErrorResponse, "description": "Meeting not found"},
    },
)
async def end_meeting(meeting: MeetingDep, body: MeetingUpdateRequest, service: MeetingServiceDep) -> MeetingResponse:
    instance = await service.update(meeting, body)
    return MeetingResponse.model_validate(instance)
