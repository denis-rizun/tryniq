from app.chat.clients.context_builder import ContextBuilder
from app.chat.constants import (
    SCOPE_NOTE_ALL,
    SCOPE_NOTE_MEETING,
    SYSTEM_PROMPT_TEMPLATE,
    AnswerHistoryMessage,
    ChatScope,
    RetrievedContext,
)


class PromptBuilder:
    def __init__(self, context_builder: ContextBuilder) -> None:
        self._context_builder = context_builder

    def build_system_prompt(self, scope: ChatScope, context: RetrievedContext) -> str:
        utterance_block, graph_block = self._context_builder.build(scope, context)
        scope_note = SCOPE_NOTE_MEETING if scope == ChatScope.MEETING else SCOPE_NOTE_ALL
        return SYSTEM_PROMPT_TEMPLATE.format(
            scope_note=scope_note,
            utterance_block=utterance_block,
            graph_block=graph_block,
        )

    @staticmethod
    def build_messages(
        system_prompt: str,
        history: list[AnswerHistoryMessage],
        query: str,
    ) -> list[dict]:
        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        for h in history:
            messages.append({"role": h.role, "content": h.text})
        messages.append({"role": "user", "content": query})
        return messages
