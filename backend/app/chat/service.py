import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

import structlog
from openai import OpenAIError
from sqlmodel import col, desc, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.chat.clients.responder import ChatResponder
from app.chat.clients.retriever import ChatRetriever
from app.chat.constants import (
    CHAT_TITLE_MAX_LEN,
    AnswerComplete,
    AnswerDelta,
    AnswerHistoryMessage,
    ChatRole,
    ChatScope,
)
from app.chat.exceptions import (
    ChatSessionNotFoundError,
    InvalidChatScopeError,
    MeetingNotFinalizedError,
)
from app.chat.models import ChatMessage, ChatSession
from app.chat.schemas import (
    ChatCitation,
    ChatMessageResponse,
    ChatSessionCreateRequest,
    ChatSessionDetailResponse,
    ChatSessionResponse,
    ChatSessionUpdateRequest,
    ChatStreamEvent,
    MessageCompletedEvent,
    MessageStartedEvent,
    StreamErrorEvent,
    TokenEvent,
)
from app.config import config
from app.meeting.constants import MeetingStatus
from app.meeting.models import Meeting

logger = structlog.get_logger()


@dataclass(slots=True)
class _StreamResult:
    text: str
    citations: list[ChatCitation]
    model: str
    error_detail: str | None


class ChatService:
    def __init__(self, session: AsyncSession, retriever: ChatRetriever, responder: ChatResponder) -> None:
        self.session = session
        self.retriever = retriever
        self.responder = responder

    async def create_session(self, data: ChatSessionCreateRequest) -> ChatSessionResponse:
        if data.scope == ChatScope.MEETING:
            if not data.meeting_id:
                raise InvalidChatScopeError()

            await self._ensure_meeting_final(data.meeting_id)
        elif data.meeting_id:
            raise InvalidChatScopeError()

        title = data.title or self._get_default_title(data.scope)
        instance = ChatSession(title=title, scope=data.scope, meeting_id=data.meeting_id)
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        logger.debug("chat session created", id=instance.id, scope=instance.scope, meeting_id=instance.meeting_id)
        return ChatSessionResponse.from_models(instance)

    async def list_sessions(self, scope: ChatScope | None, meeting_id: UUID | None) -> list[ChatSessionResponse]:
        stmt = select(ChatSession).order_by(desc(col(ChatSession.updated_at)))
        if scope:
            stmt = stmt.where(col(ChatSession.scope) == scope)
        if meeting_id:
            stmt = stmt.where(col(ChatSession.meeting_id) == meeting_id)

        sessions = (await self.session.exec(stmt)).all()
        chat_schemas: list[ChatSessionResponse] = []
        for s in sessions:
            last = await self._get_latest_message(s.id)
            chat_schemas.append(ChatSessionResponse.from_models(s, last))
        return chat_schemas

    async def retrieve(self, id: UUID) -> ChatSession:
        instance = (await self.session.exec(select(ChatSession).where(col(ChatSession.id) == id))).one_or_none()
        if not instance:
            raise ChatSessionNotFoundError()

        return instance

    async def retrieve_with_messages(self, session: ChatSession) -> ChatSessionDetailResponse:
        messages = await self._get_all_messages_by_session(session.id)
        raw = {**session.model_dump(), "messages": [ChatMessageResponse.from_model(m) for m in messages]}
        return ChatSessionDetailResponse.model_validate(raw)

    async def rename_session(self, session: ChatSession, data: ChatSessionUpdateRequest) -> ChatSessionResponse:
        session.title = data.title
        self.session.add(session)
        await self.session.commit()
        await self.session.refresh(session)
        last = await self._get_latest_message(session.id)
        return ChatSessionResponse.from_models(session, last)

    async def delete_session(self, session: ChatSession) -> None:
        await self.session.delete(session)
        await self.session.commit()

    async def stream(self, session: ChatSession, text: str) -> AsyncIterator[bytes]:
        try:
            async for event in self._stream_message(session, text):
                payload = event.model_dump(mode="json")
                yield f"event: {payload['kind']}\ndata: ".encode() + json.dumps(payload).encode() + b"\n\n"
        except GeneratorExit:
            logger.debug("chat sse client disconnected", session_id=session.id)

    async def _stream_message(self, session: ChatSession, text: str) -> AsyncIterator[ChatStreamEvent]:
        if session.scope == ChatScope.MEETING and session.meeting_id:
            await self._ensure_meeting_final(session.meeting_id)

        user_message = await self._persist_user_message(session, text)
        history = await self._get_recent_history(session_id=session.id, exclude_id=user_message.id)
        context = await self.retriever.retrieve(query=text, scope=session.scope, meeting_id=session.meeting_id)
        assistant = await self._persist_assistant_placeholder(session.id)

        yield MessageStartedEvent(
            user_message=ChatMessageResponse.from_model(user_message),
            assistant_message_id=assistant.id,
        )

        started = time.monotonic()
        result = _StreamResult(text="", citations=[], model=config.chat.LLM_MODEL, error_detail=None)
        try:
            async for event in self.responder.stream_answer(text, session.scope, history, context, session.id):
                if isinstance(event, AnswerDelta):
                    result.text += event.text
                    yield TokenEvent(delta=event.text)
                elif isinstance(event, AnswerComplete):
                    result.text = event.text
                    result.citations = event.citations
                    result.model = event.model
        except OpenAIError:
            logger.exception("chat generation failed", session_id=session.id)
            result.error_detail = "generation_failed"
            result.text = result.text.strip() or "I couldn't generate a response."

        await self._finalize_assistant(session, assistant, result, started)
        if result.error_detail:
            yield StreamErrorEvent(detail=result.error_detail)
            return

        yield MessageCompletedEvent(message=ChatMessageResponse.from_model(assistant, result.citations))

    async def _persist_user_message(self, session: ChatSession, text: str) -> ChatMessage:
        is_first = await self._is_first_message(session.id)
        message = ChatMessage(session_id=session.id, role=ChatRole.USER, text=text, citations=[])
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)

        if is_first:
            session.title = self._derive_title(text)
            self.session.add(session)
            await self.session.commit()
            await self.session.refresh(session)

        return message

    async def _persist_assistant_placeholder(self, session_id: UUID) -> ChatMessage:
        assistant = ChatMessage(session_id=session_id, role=ChatRole.ASSISTANT, text="", citations=[])
        self.session.add(assistant)
        await self.session.commit()
        await self.session.refresh(assistant)
        return assistant

    async def _finalize_assistant(
        self,
        session: ChatSession,
        assistant: ChatMessage,
        result: _StreamResult,
        started: float,
    ) -> None:
        assistant.text = result.text
        assistant.citations = [c.model_dump(mode="json") for c in result.citations]
        assistant.model = result.model
        assistant.latency_ms = int((time.monotonic() - started) * 1000)
        self.session.add(assistant)
        session.updated_at = assistant.created_at
        self.session.add(session)
        await self.session.commit()
        await self.session.refresh(assistant)

    async def _ensure_meeting_final(self, meeting_id: UUID) -> None:
        meeting = (await self.session.exec(select(Meeting).where(col(Meeting.id) == meeting_id))).one_or_none()
        if not meeting or meeting.status != MeetingStatus.FINAL:
            raise MeetingNotFinalizedError()

    async def _is_first_message(self, session_id: UUID) -> bool:
        stmt = select(ChatMessage.id).where(col(ChatMessage.session_id) == session_id).limit(1)
        existing = (await self.session.exec(stmt)).one_or_none()
        return not existing

    @staticmethod
    def _derive_title(text: str) -> str:
        head = text.splitlines()[0] if text else ""
        head = " ".join(head.split())
        if len(head) <= CHAT_TITLE_MAX_LEN:
            return head or "New conversation"
        return head[: CHAT_TITLE_MAX_LEN - 1].rstrip() + "…"

    async def _get_latest_message(self, session_id: UUID) -> ChatMessage | None:
        stmt = (
            select(ChatMessage)
            .where(col(ChatMessage.session_id) == session_id)
            .order_by(desc(col(ChatMessage.created_at)))
            .limit(1)
        )
        return (await self.session.exec(stmt)).one_or_none()

    async def _get_all_messages_by_session(self, session_id: UUID) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage).where(col(ChatMessage.session_id) == session_id).order_by(col(ChatMessage.created_at))
        )
        return list((await self.session.exec(stmt)).all())

    async def _get_recent_history(self, session_id: UUID, exclude_id: UUID) -> list[AnswerHistoryMessage]:
        stmt = (
            select(ChatMessage)
            .where(col(ChatMessage.session_id) == session_id)
            .where(col(ChatMessage.id) != exclude_id)
            .where(col(ChatMessage.text) != "")
            .order_by(desc(col(ChatMessage.created_at)))
            .limit(config.chat.MAX_HISTORY)
        )
        rows = list((await self.session.exec(stmt)).all())
        rows.reverse()
        return [AnswerHistoryMessage(role=str(m.role), text=m.text) for m in rows]

    @staticmethod
    def _get_default_title(scope: ChatScope) -> str:
        return "New conversation" if scope == ChatScope.MEETING else "New cross-meeting chat"
