from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.chat.models import ChatSession
from app.chat.services.chat import ChatService
from app.chat.services.context_builder import ContextBuilder
from app.chat.services.prompt_builder import PromptBuilder
from app.chat.services.responder import ChatResponder
from app.chat.services.retrieval import ChatRetriever
from app.chat.services.streaming import ChatMessageStreamer
from app.db import SessionDep


@lru_cache(maxsize=1)
def get_context_builder() -> ContextBuilder:
    return ContextBuilder()


@lru_cache(maxsize=1)
def get_prompt_builder() -> PromptBuilder:
    return PromptBuilder(get_context_builder())


@lru_cache(maxsize=1)
def get_responder() -> ChatResponder:
    return ChatResponder(get_prompt_builder())


ChatResponderDep = Annotated[ChatResponder, Depends(get_responder)]


def get_chat_retriever(session: SessionDep) -> ChatRetriever:
    return ChatRetriever(session)


ChatRetrieverDep = Annotated[ChatRetriever, Depends(get_chat_retriever)]


def get_chat_streamer(
    session: SessionDep,
    retriever: ChatRetrieverDep,
    responder: ChatResponderDep,
) -> ChatMessageStreamer:
    return ChatMessageStreamer(session, retriever, responder)


ChatMessageStreamerDep = Annotated[ChatMessageStreamer, Depends(get_chat_streamer)]


def get_chat_service(
    session: SessionDep,
    streamer: ChatMessageStreamerDep,
) -> ChatService:
    return ChatService(session, streamer)


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]


async def get_chat_session(id: UUID, service: ChatServiceDep) -> ChatSession:
    return await service.retrieve(id)


ChatSessionDep = Annotated[ChatSession, Depends(get_chat_session)]
