from fastapi import APIRouter
from starlette import status

from app.core.base_schema import ErrorResponse
from app.meeting.dependencies import MeetingDep
from app.participant.dependencies import ParticipantServiceDep
from app.participant.schemas import ParticipantResponse

router = APIRouter(tags=["Participants"])


@router.get(
    path="/meetings/{id}/participants",
    response_model=list[ParticipantResponse],
    status_code=status.HTTP_200_OK,
    summary="List meeting participants",
    description="List all participants for a meeting.",
    responses={404: {"model": ErrorResponse, "description": "Meeting not found"}},
)
async def list_participants(meeting: MeetingDep, service: ParticipantServiceDep) -> list[ParticipantResponse]:
    result = await service.list(meeting)
    return [ParticipantResponse.model_validate(p) for p in result]
