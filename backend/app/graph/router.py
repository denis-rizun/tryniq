from fastapi import APIRouter
from starlette import status

from app.core.base_schema import ErrorResponse
from app.graph.dependencies import GraphServiceDep
from app.graph.schemas import GraphResponse
from app.meeting.dependencies import MeetingDep

router = APIRouter(prefix="/meetings", tags=["graph"])


@router.get(
    path="/{id}/graph",
    response_model=GraphResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Meeting Graph",
    description="Return all graph nodes and edges for a meeting.",
    responses={
        404: {"model": ErrorResponse, "description": "Meeting not found"},
    },
)
async def get_meeting_graph(meeting: MeetingDep, service: GraphServiceDep) -> GraphResponse:
    return await service.get_graph(meeting.id)
