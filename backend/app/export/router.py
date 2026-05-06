from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from starlette import status

from app.core.base_schema import ErrorResponse
from app.export.constants import MEDIA_TYPE
from app.export.dependencies import ExportServiceDep
from app.meeting.dependencies import MeetingDep

router = APIRouter(prefix="/meetings", tags=["export"])


@router.get(
    path="/{id}/export",
    response_class=PlainTextResponse,
    status_code=status.HTTP_200_OK,
    summary="Export meeting as Markdown",
    description="Render the meeting (summary, decisions, action items, questions, topics, transcript) as Markdown.",
    responses={
        200: {"content": {MEDIA_TYPE: {}}},
        404: {"model": ErrorResponse, "description": "Meeting not found"},
    },
)
async def export_meeting_markdown(
    meeting: MeetingDep,
    service: ExportServiceDep,
    include: str | None = None,
) -> PlainTextResponse:
    export = await service.export_markdown(meeting, include)
    return PlainTextResponse(
        content=export.body,
        media_type=export.media_type,
        headers={"Content-Disposition": f'attachment; filename="{export.filename}"'},
    )
