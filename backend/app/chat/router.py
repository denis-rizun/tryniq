from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from starlette import status

from app.chat.constants import ChatScope
from app.chat.dependencies import ChatServiceDep, ChatSessionDep
from app.chat.schemas import (
    ChatMessageCreateRequest,
    ChatSessionCreateRequest,
    ChatSessionDetailResponse,
    ChatSessionResponse,
    ChatSessionUpdateRequest,
)
from app.core.base_schema import ErrorResponse

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post(
    path="/sessions",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create chat session",
    description="Create a new chat session. Scope 'meeting' requires meeting_id.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid scope"},
        409: {"model": ErrorResponse, "description": "Meeting not finalized"},
    },
)
async def create_session(body: ChatSessionCreateRequest, service: ChatServiceDep) -> ChatSessionResponse:
    return await service.create_session(body)


@router.get(
    path="/sessions",
    response_model=list[ChatSessionResponse],
    status_code=status.HTTP_200_OK,
    summary="List chat sessions",
    description="List chat sessions, ordered by most recent activity.",
)
async def list_sessions(
    service: ChatServiceDep,
    scope: ChatScope | None = None,
    meeting_id: UUID | None = None,
) -> list[ChatSessionResponse]:
    return await service.list_sessions(scope=scope, meeting_id=meeting_id)


@router.get(
    path="/sessions/{id}",
    response_model=ChatSessionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get chat session",
    description="Get a chat session with all its messages.",
    responses={404: {"model": ErrorResponse, "description": "Session not found"}},
)
async def get_session(session: ChatSessionDep, service: ChatServiceDep) -> ChatSessionDetailResponse:
    return await service.retrieve_with_messages(session)


@router.patch(
    path="/sessions/{id}",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Rename chat session",
    description="Rename a chat session.",
    responses={404: {"model": ErrorResponse, "description": "Session not found"}},
)
async def rename_session(
    body: ChatSessionUpdateRequest,
    session: ChatSessionDep,
    service: ChatServiceDep,
) -> ChatSessionResponse:
    return await service.rename_session(session, body)


@router.delete(
    path="/sessions/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete chat session",
    description="Delete a chat session and all its messages.",
    responses={404: {"model": ErrorResponse, "description": "Session not found"}},
)
async def delete_session(session: ChatSessionDep, service: ChatServiceDep) -> None:
    await service.delete_session(session)


@router.post(
    path="/sessions/{id}/messages",
    status_code=status.HTTP_200_OK,
    summary="Send chat message (SSE stream)",
    description="Send a user message and stream the assistant response over SSE.",
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
        409: {"model": ErrorResponse, "description": "Meeting not finalized"},
    },
)
async def send_message(
    body: ChatMessageCreateRequest,
    session: ChatSessionDep,
    service: ChatServiceDep,
) -> StreamingResponse:
    return StreamingResponse(
        service.stream(session, body.text),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
