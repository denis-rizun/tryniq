from fastapi import APIRouter
from starlette import status

from app.core.base_schema import ErrorResponse
from app.meeting.dependencies import MeetingDep
from app.participant.dependencies import ParticipantServiceDep
from app.participant.schemas import ParticipantResponse, PersonListItem, PersonUtteranceItem

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


@router.get(
    path="/people",
    response_model=list[PersonListItem],
    status_code=status.HTTP_200_OK,
    summary="List people",
    description="List people aggregated across meetings (deduped by name).",
)
async def list_people(service: ParticipantServiceDep) -> list[PersonListItem]:
    return await service.list_people()


@router.get(
    path="/people/utterances",
    response_model=list[PersonUtteranceItem],
    status_code=status.HTTP_200_OK,
    summary="List recent utterances for a person",
    description="Recent transcript utterances for any participant with the given name.",
)
async def list_person_utterances(
    service: ParticipantServiceDep,
    name: str,
    limit: int = 6,
) -> list[PersonUtteranceItem]:
    return await service.list_person_utterances(name, limit)
