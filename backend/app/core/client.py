from collections.abc import AsyncIterator
from functools import lru_cache

import structlog
from langfuse import Langfuse
from langfuse.openai import AsyncOpenAI as LangfuseAsyncOpenAI
from openai.types.chat import ChatCompletionChunk
from pydantic import BaseModel, ValidationError

from app.config import config
from app.core.constants import ChatRequest, StructuredRequest
from app.core.exceptions import AIValidationError

logger = structlog.get_logger()


class AIClient:
    def __init__(self) -> None:
        self.langfuse = Langfuse(
            public_key=config.ai.LANGFUSE_PUBLIC_KEY.get_secret_value(),
            secret_key=config.ai.LANGFUSE_SECRET_KEY.get_secret_value(),
            host=config.ai.LANGFUSE_HOST,
        )
        self.openai = LangfuseAsyncOpenAI(api_key=config.ai.OPENAI_API_KEY.get_secret_value())

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        response = await self.openai.embeddings.create(model=config.ai.EMBED_MODEL, input=texts)
        return [item.embedding for item in response.data]

    async def complete_structured[T: BaseModel](self, request: StructuredRequest) -> T:
        response = await self.openai.chat.completions.create(
            model=request.model,
            max_completion_tokens=request.max_tokens,
            messages=[
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": request.kind, "schema": request.schema, "strict": True},
            },
            **request.langfuse_kwargs,
        )
        choices = response.choices or []
        if not choices:
            raise AIValidationError(kind=request.kind, detail="AI returned no choices")

        content = choices[0].message.content or ""
        if not content.strip():
            raise AIValidationError(kind=request.kind, detail="AI returned empty content")

        try:
            return request.dto.model_validate_json(content)
        except ValidationError as exc:
            logger.warning("AI structured output failed validation", kind=request.kind, errors=str(exc)[:500])
            raise AIValidationError(kind=request.kind, detail=str(exc), raw=content) from exc

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[ChatCompletionChunk]:
        stream = await self.openai.chat.completions.create(
            model=request.model,
            messages=request.messages,
            max_completion_tokens=request.max_tokens,
            stream=True,
            **request.langfuse_kwargs,
        )
        async for chunk in stream:
            yield chunk


@lru_cache(maxsize=1)
def get_ai_client() -> AIClient:
    return AIClient()
