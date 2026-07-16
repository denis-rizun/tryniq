import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import structlog

from app.chat.constants import (
    CROSS_LABEL_MAX_LEN,
    GRAPH_REF_PATTERN,
    REF_PATTERN,
    ChatScope,
)
from app.chat.schemas import ChatCitation
from app.chat.services.context_builder import format_mmss
from app.chat.services.retrieval import RetrievedContext, UtteranceHit
from app.config import config
from app.core.client import get_ai_client
from app.core.constants import AIRequestKind, ChatRequest

if TYPE_CHECKING:
    from app.chat.services.prompt_builder import PromptBuilder

logger = structlog.get_logger()


@dataclass(slots=True)
class AnswerHistoryMessage:
    role: str
    text: str


@dataclass(slots=True)
class AnswerDelta:
    text: str


@dataclass(slots=True)
class AnswerComplete:
    text: str
    citations: list[ChatCitation]
    model: str


type AnswerEvent = AnswerDelta | AnswerComplete


class ChatResponder:
    def __init__(self, prompt_builder: "PromptBuilder") -> None:
        self.prompt_builder = prompt_builder

    async def stream_answer(
        self,
        query: str,
        scope: ChatScope,
        history: list[AnswerHistoryMessage],
        context: RetrievedContext,
        session_id: UUID | None = None,
    ) -> AsyncIterator[AnswerEvent]:
        system_prompt = self.prompt_builder.build_system_prompt(scope)
        user_content = self.prompt_builder.build_user_message(scope, context, query)
        messages = self.prompt_builder.build_messages(system_prompt, history, user_content)

        ai_client = get_ai_client()
        model = config.chat.LLM_MODEL
        request = ChatRequest(
            kind=AIRequestKind.CHAT_STREAM_ANSWER,
            messages=messages,
            model=model,
            max_tokens=config.chat.MAX_OUTPUT_TOKENS,
            langfuse_kwargs=_build_langfuse_kwargs(scope, session_id),
        )

        full_text = ""
        async for chunk in ai_client.stream_chat(request):
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta.content or ""
            if not delta:
                continue

            full_text += delta
            yield AnswerDelta(text=delta)

        rendered_text, citations = self._finalize(full_text, scope, context)
        yield AnswerComplete(text=rendered_text, citations=citations, model=model)

    @staticmethod
    def _finalize(
        text: str,
        scope: ChatScope,
        context: RetrievedContext,
    ) -> tuple[str, list[ChatCitation]]:
        ref_to_hit = {hit.ref: hit for hit in context.utterances}
        used: dict[UUID, ChatCitation] = {}
        order: list[UUID] = []

        def add(hit: UtteranceHit) -> str:
            label = _format_citation_label(scope, hit)
            if hit.utterance_id not in used:
                used[hit.utterance_id] = ChatCitation(
                    utterance_id=hit.utterance_id,
                    meeting_id=hit.meeting_id,
                    meeting_title=hit.meeting_title,
                    meeting_started_at=hit.meeting_started_at,
                    t_start=hit.t_start,
                    t_end=hit.t_end,
                    speaker=hit.speaker,
                    text=hit.text,
                    label=label,
                )
                order.append(hit.utterance_id)
            return label

        def replace_u(match: re.Match[str]) -> str:
            hit = ref_to_hit.get(match.group(1))
            if not hit:
                return ""
            return f"[{add(hit)}]"

        label_to_hit: dict[str, UtteranceHit] = {}
        for hit in context.utterances:
            label_to_hit[_format_citation_label(scope, hit)] = hit
            label_to_hit[format_mmss(hit.t_start)] = hit

        def replace_bare(match: re.Match[str]) -> str:
            label = match.group(1).strip()
            hit = label_to_hit.get(label)
            if not hit:
                return f"[{label}]"
            return f"[{add(hit)}]"

        rendered = REF_PATTERN.sub(replace_u, text)
        rendered = GRAPH_REF_PATTERN.sub("", rendered)
        if label_to_hit:
            bare_alts = sorted({re.escape(k) for k in label_to_hit}, key=len, reverse=True)
            bare_pattern = re.compile(r"\[(" + "|".join(bare_alts) + r")\]")
            rendered = bare_pattern.sub(replace_bare, rendered)
        rendered = re.sub(r"[ \t]+\.", ".", rendered)
        rendered = re.sub(r"\s+\n", "\n", rendered)
        rendered = rendered.strip()
        citations = [used[uid] for uid in order]
        return rendered, citations


def _format_citation_label(scope: ChatScope, hit: UtteranceHit) -> str:
    if scope == ChatScope.MEETING:
        return format_mmss(hit.t_start)

    title = (hit.meeting_title or "").strip()
    if title:
        if len(title) > CROSS_LABEL_MAX_LEN:
            return title[: CROSS_LABEL_MAX_LEN - 1].rstrip() + "…"
        return title
    if hit.meeting_started_at:
        return _format_date(hit.meeting_started_at)
    return format_mmss(hit.t_start)


def _format_date(dt: datetime) -> str:
    return dt.date().isoformat()


def _build_langfuse_kwargs(scope: ChatScope, session_id: UUID | None) -> dict:
    metadata: dict = {"scope": str(scope), "tags": ["chat", str(scope)]}
    if session_id:
        metadata["session_id"] = str(session_id)
    return {"name": "chat.stream_answer", "metadata": metadata}
