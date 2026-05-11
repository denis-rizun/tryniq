from app.chat.clients.context_builder import ContextBuilder
from app.chat.constants import (
    SCOPE_NOTE_ALL,
    SCOPE_NOTE_MEETING,
    AnswerHistoryMessage,
    ChatScope,
    RetrievedContext,
)
from app.core.constants import CHAT_SYSTEM_PROMPT_TEMPLATE, CHAT_USER_CONTEXT_TEMPLATE


class PromptBuilder:
    def __init__(self, context_builder: ContextBuilder) -> None:
        self._context_builder = context_builder

    @staticmethod
    def build_system_prompt(scope: ChatScope) -> str:
        scope_note = SCOPE_NOTE_MEETING if scope == ChatScope.MEETING else SCOPE_NOTE_ALL
        return CHAT_SYSTEM_PROMPT_TEMPLATE.format(scope_note=scope_note)

    def build_user_message(self, scope: ChatScope, context: RetrievedContext, query: str) -> str:
        utterance_block, graph_block = self._context_builder.build(scope, context)
        return CHAT_USER_CONTEXT_TEMPLATE.format(
            utterance_block=utterance_block,
            graph_block=graph_block,
            query=query,
        )

    @staticmethod
    def build_messages(
        system_prompt: str,
        history: list[AnswerHistoryMessage],
        user_content: str,
    ) -> list[dict]:
        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        for h in history:
            messages.append({"role": h.role, "content": h.text})
        messages.append({"role": "user", "content": user_content})
        return messages
