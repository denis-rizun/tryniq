from collections.abc import AsyncIterator
from uuid import UUID

import structlog
from sqlmodel import col, desc, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.chat.constants import ChatScope
from app.chat.exceptions import ChatSessionNotFoundError, InvalidChatScopeError
from app.chat.models import ChatMessage, ChatSession
from app.chat.schemas import (
    ChatMessageResponse,
    ChatSessionCreateRequest,
    ChatSessionDetailResponse,
    ChatSessionResponse,
    ChatSessionUpdateRequest,
)
from app.chat.services.streaming import ChatMessageStreamer

logger = structlog.get_logger()


class ChatService:
    def __init__(self, session: AsyncSession, streamer: ChatMessageStreamer) -> None:
        self.session = session
        self.streamer = streamer

    async def create_session(self, data: ChatSessionCreateRequest) -> ChatSessionResponse:
        if (data.scope == ChatScope.MEETING and not data.meeting_id) or (
            data.scope != ChatScope.MEETING and data.meeting_id
        ):
            raise InvalidChatScopeError()

        if data.meeting_id:
            await self.streamer.ensure_meeting_final(data.meeting_id)

        instance = ChatSession(
            title=data.title or self._get_default_title(data.scope), scope=data.scope, meeting_id=data.meeting_id
        )
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        logger.debug("chat session created", id=instance.id, scope=instance.scope, meeting_id=instance.meeting_id)
        return ChatSessionResponse.from_models(instance)

    async def list_sessions(self, scope: ChatScope | None, meeting_id: UUID | None) -> list[ChatSessionResponse]:
        statement = select(ChatSession).order_by(desc(col(ChatSession.updated_at)))
        if scope:
            statement = statement.where(col(ChatSession.scope) == scope)
        if meeting_id:
            statement = statement.where(col(ChatSession.meeting_id) == meeting_id)
        sessions = (await self.session.exec(statement)).all()
        return [
            ChatSessionResponse.from_models(session, await self._latest_message(session.id)) for session in sessions
        ]

    async def retrieve(self, id: UUID) -> ChatSession:
        session = (await self.session.exec(select(ChatSession).where(col(ChatSession.id) == id))).one_or_none()
        if session is None:
            raise ChatSessionNotFoundError()
        return session

    async def retrieve_with_messages(self, session: ChatSession) -> ChatSessionDetailResponse:
        statement = (
            select(ChatMessage).where(col(ChatMessage.session_id) == session.id).order_by(col(ChatMessage.created_at))
        )
        messages = (await self.session.exec(statement)).all()
        return ChatSessionDetailResponse.model_validate(
            {**session.model_dump(), "messages": [ChatMessageResponse.from_model(message) for message in messages]}
        )

    async def rename_session(self, session: ChatSession, data: ChatSessionUpdateRequest) -> ChatSessionResponse:
        session.title = data.title
        self.session.add(session)
        await self.session.commit()
        await self.session.refresh(session)
        return ChatSessionResponse.from_models(session, await self._latest_message(session.id))

    async def delete_session(self, session: ChatSession) -> None:
        await self.session.delete(session)
        await self.session.commit()

    def stream(self, session: ChatSession, text: str) -> AsyncIterator[bytes]:
        return self.streamer.stream(session, text)

    @staticmethod
    def _get_default_title(scope: ChatScope) -> str:
        return "New conversation" if scope == ChatScope.MEETING else "New cross-meeting chat"

    async def _latest_message(self, session_id: UUID) -> ChatMessage | None:
        statement = (
            select(ChatMessage)
            .where(col(ChatMessage.session_id) == session_id)
            .order_by(desc(col(ChatMessage.created_at)))
            .limit(1)
        )
        return (await self.session.exec(statement)).one_or_none()
