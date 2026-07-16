from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile
from starlette import status

from app.core.base_schema import ErrorResponse
from app.upload.dependencies import UploadServiceDep
from app.upload.schemas import UploadResponse

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.post(
    path="/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload recording",
    description="Upload an audio/video recording to be diarized, transcribed, and turned into a graph.",
    responses={
        400: {"model": ErrorResponse, "description": "Unsupported, oversized, or overlong upload"},
    },
)
async def upload_meeting(
    service: UploadServiceDep,
    file: Annotated[UploadFile, File(...)],
    title: Annotated[str | None, Form()] = None,
) -> UploadResponse:
    meeting_id = await service.create(file, title)
    return UploadResponse(meeting_id=meeting_id)
