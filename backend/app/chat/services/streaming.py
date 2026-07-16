import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

import structlog
from openai import OpenAIError
from sqlmodel import col, desc, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.chat.constants import CHAT_TITLE_MAX_LEN, ChatRole, ChatScope
from app.chat.exceptions import MeetingNotFinalizedError
from app.chat.models import ChatMessage, ChatSession
from app.chat.schemas import (
    ChatCitation,
    ChatMessageResponse,
    ChatStreamEvent,
    MessageCompletedEvent,
    MessageStartedEvent,
    StreamErrorEvent,
    TokenEvent,
)
from app.chat.services.responder import AnswerComplete, AnswerDelta, AnswerHistoryMessage, ChatResponder
from app.chat.services.retrieval import ChatRetriever
from app.config import config
from app.meeting.constants import MeetingStatus
from app.meeting.models import Meeting

logger = structlog.get_logger()


@dataclass(slots=True)
class _StreamResult:
    text: str
    citations: list[ChatCitation]
    model: str
    error_detail: str | None = None


class ChatMessageStreamer:
    def __init__(self, session: AsyncSession, retriever: ChatRetriever, responder: ChatResponder) -> None:
        self.session = session
        self.retriever = retriever
        self.responder = responder

    async def stream(self, session: ChatSession, text: str) -> AsyncIterator[bytes]:
        try:
            async for event in self._stream_message(session, text):
                payload = event.model_dump(mode="json")
                yield f"event: {payload['kind']}\ndata: ".encode() + json.dumps(payload).encode() + b"\n\n"
        except GeneratorExit:
            logger.debug("chat sse client disconnected", session_id=session.id)

    async def ensure_meeting_final(self, meeting_id: UUID) -> None:
        meeting = (await self.session.exec(select(Meeting).where(col(Meeting.id) == meeting_id))).one_or_none()
        if meeting is None or meeting.status != MeetingStatus.FINAL:
            raise MeetingNotFinalizedError()

    async def _stream_message(self, session: ChatSession, text: str) -> AsyncIterator[ChatStreamEvent]:
        if session.scope == ChatScope.MEETING and session.meeting_id:
            await self.ensure_meeting_final(session.meeting_id)
        user = await self._persist_user_message(session, text)
        history = await self._recent_history(session.id, user.id)
        context = await self.retriever.retrieve(text, session.scope, session.meeting_id)
        assistant = await self._persist_assistant_placeholder(session.id)
        yield MessageStartedEvent(user_message=ChatMessageResponse.from_model(user), assistant_message_id=assistant.id)
        started = time.monotonic()
        result = _StreamResult(text="", citations=[], model=config.chat.LLM_MODEL)
        try:
            async for event in self.responder.stream_answer(text, session.scope, history, context, session.id):
                if isinstance(event, AnswerDelta):
                    result.text += event.text
                    yield TokenEvent(delta=event.text)
                elif isinstance(event, AnswerComplete):
                    result.text, result.citations, result.model = event.text, event.citations, event.model
        except OpenAIError:
            logger.exception("chat generation failed", session_id=session.id)
            result.error_detail, result.text = (
                "generation_failed",
                result.text.strip() or "I couldn't generate a response.",
            )
        await self._finalize_assistant(session, assistant, result, started)
        if result.error_detail:
            yield StreamErrorEvent(detail=result.error_detail)
        else:
            yield MessageCompletedEvent(message=ChatMessageResponse.from_model(assistant, result.citations))

    async def _persist_user_message(self, session: ChatSession, text: str) -> ChatMessage:
        first = (
            await self.session.exec(select(ChatMessage.id).where(col(ChatMessage.session_id) == session.id).limit(1))
        ).one_or_none() is None
        message = ChatMessage(session_id=session.id, role=ChatRole.USER, text=text, citations=[])
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        if first:
            session.title = self._derive_title(text)
            self.session.add(session)
            await self.session.commit()
        return message

    async def _persist_assistant_placeholder(self, session_id: UUID) -> ChatMessage:
        message = ChatMessage(session_id=session_id, role=ChatRole.ASSISTANT, text="", citations=[])
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def _finalize_assistant(
        self, session: ChatSession, assistant: ChatMessage, result: _StreamResult, started: float
    ) -> None:
        assistant.text, assistant.model = result.text, result.model
        assistant.citations = [citation.model_dump(mode="json") for citation in result.citations]
        assistant.latency_ms = int((time.monotonic() - started) * 1000)
        session.updated_at = assistant.created_at
        self.session.add_all([assistant, session])
        await self.session.commit()
        await self.session.refresh(assistant)

    async def _recent_history(self, session_id: UUID, exclude_id: UUID) -> list[AnswerHistoryMessage]:
        statement = (
            select(ChatMessage)
            .where(col(ChatMessage.session_id) == session_id)
            .where(col(ChatMessage.id) != exclude_id)
            .where(col(ChatMessage.text) != "")
            .order_by(desc(col(ChatMessage.created_at)))
            .limit(config.chat.MAX_HISTORY)
        )
        rows = list((await self.session.exec(statement)).all())
        return [AnswerHistoryMessage(role=str(message.role), text=message.text) for message in reversed(rows)]

    @staticmethod
    def _derive_title(text: str) -> str:
        title = " ".join((text.splitlines()[0] if text else "").split())
        if len(title) <= CHAT_TITLE_MAX_LEN:
            return title or "New conversation"
        return title[: CHAT_TITLE_MAX_LEN - 1].rstrip() + "…"
