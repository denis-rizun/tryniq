from functools import lru_cache

import structlog
from openai import AsyncOpenAI

from app.config import config

logger = structlog.get_logger()


class EmbeddingClient:
    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        if not self._client:
            self._client = AsyncOpenAI(api_key=config.graph.OPENAI_API_KEY.get_secret_value())
        return self._client

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        response = await self.client.embeddings.create(model=config.graph.EMBED_MODEL, input=texts)
        return [item.embedding for item in response.data]


@lru_cache(maxsize=1)
def get_embedding_client() -> EmbeddingClient:
    return EmbeddingClient()
