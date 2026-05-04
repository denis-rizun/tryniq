import json
from functools import lru_cache

import structlog
from anthropic import AsyncAnthropic
from mistralai.client.sdk import Mistral
from pydantic import ValidationError

from app.config import config
from app.graph.constants import ANTHROPIC_TOOL, MISTRAL_TOOL, SYSTEM_PROMPT, TOOL_NAME
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
            args = _coerce_json(call.function.arguments)
            if not isinstance(args, dict):
                continue
            ops = _coerce_json(args.get("ops", []))
            if not isinstance(ops, list):
                continue
            return list(ops)
        return []


def _coerce_json(value: object) -> object:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    repaired = _extract_balanced_json(text)
    if repaired is None:
        logger.warning("could not parse LLM tool args as JSON", preview=text[:300])
        return None
    try:
        return json.loads(repaired)
    except json.JSONDecodeError as exc:
        logger.warning("repaired LLM JSON still invalid", error=str(exc), preview=repaired[:300])
        return None


def _extract_balanced_json(text: str) -> str | None:
    start, open_ch, close_ch = _find_json_start(text)
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            in_string, escape = _step_in_string(ch, escape)
            continue
        if ch == '"':
            in_string = True
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _find_json_start(text: str) -> tuple[int, str, str]:
    obj = text.find("{")
    arr = text.find("[")
    if obj < 0 and arr < 0:
        return -1, "", ""
    if obj < 0 or (0 <= arr < obj):
        return arr, "[", "]"
    return obj, "{", "}"


def _step_in_string(ch: str, escape: bool) -> tuple[bool, bool]:
    if escape:
        return True, False
    if ch == "\\":
        return True, True
    if ch == '"':
        return False, False
    return True, False


@lru_cache(maxsize=1)
def get_extractor() -> GraphExtractor:
    return GraphExtractor()
