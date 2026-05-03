import json
from functools import lru_cache

import structlog
from anthropic import AsyncAnthropic
from mistralai.client.sdk import Mistral
from pydantic import ValidationError

from app.config import config
from app.graph.constants import SYSTEM_PROMPT, TOOL_NAME, ANTHROPIC_TOOL, MISTRAL_TOOL
from app.graph.exceptions import InvalidGraphOperationError
from app.graph.schemas import GRAPH_OPERATIONS_ADAPTER, GraphOperation

logger = structlog.get_logger()


class GraphExtractor:
    def __init__(self) -> None:
        self._anthropic: AsyncAnthropic | None = None
        self._mistral: Mistral | None = None

    @property
    def anthropic_client(self) -> AsyncAnthropic:
        if self._anthropic is None:
            self._anthropic = AsyncAnthropic(api_key=config.graph.ANTHROPIC_API_KEY.get_secret_value())
        return self._anthropic

    @property
    def mistral_client(self) -> Mistral:
        if self._mistral is None:
            self._mistral = Mistral(api_key=config.graph.MISTRAL_API_KEY.get_secret_value())
        return self._mistral

    async def extract(self, window_text: str) -> list[GraphOperation]:
        if config.graph.LLM_PROVIDER == "mistral":
            raw_operations = await self._extract_mistral(window_text)
        else:
            raw_operations = await self._extract_anthropic(window_text)
        try:
            return GRAPH_OPERATIONS_ADAPTER.validate_python(raw_operations)
        except ValidationError as e:
            logger.warning("Invalid LLM operation shape", errors=str(e))
            raise InvalidGraphOperationError() from e

    async def _extract_anthropic(self, window_text: str) -> list[dict]:
        message = await self.anthropic_client.messages.create(
            model=config.graph.LLM_MODEL,
            max_tokens=config.graph.LLM_MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=[ANTHROPIC_TOOL],
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=[{"role": "user", "content": window_text}],
        )
        for block in getattr(message, "content", []) or []:
            if getattr(block, "type", None) == "tool_use":
                payload = getattr(block, "input", {}) or {}
                ops = payload.get("ops", [])
                if isinstance(ops, str):
                    ops = json.loads(ops)
                return list(ops)
        return []

    async def _extract_mistral(self, window_text: str) -> list[dict]:
        response = await self.mistral_client.chat.complete_async(
            model=config.graph.LLM_MODEL,
            max_tokens=config.graph.LLM_MAX_TOKENS,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": window_text},
            ],
            tools=[MISTRAL_TOOL],
            tool_choice="any",
        )
        choices = response.choices or []
        if not choices:
            return []

        for call in choices[0].message.tool_calls or []:
            args = call.function.arguments
            if isinstance(args, str):
                args = json.loads(args)
            ops = (args or {}).get("ops", [])
            if isinstance(ops, str):
                ops = json.loads(ops)
            return list(ops)
        return []


@lru_cache(maxsize=1)
def get_extractor() -> GraphExtractor:
    return GraphExtractor()
