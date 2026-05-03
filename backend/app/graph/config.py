from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import BASE_MODEL_CONFIG


class GraphSettings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_MODEL_CONFIG, env_prefix="GRAPH_")

    LLM_PROVIDER: Literal["anthropic", "mistral"] = "mistral"
    ANTHROPIC_API_KEY: SecretStr = SecretStr("")
    MISTRAL_API_KEY: SecretStr = SecretStr("")
    OPENAI_API_KEY: SecretStr = SecretStr("")
    LLM_MODEL: str = "mistral-large-latest"
    LLM_MAX_TOKENS: int = 4096
    EMBED_MODEL: str = "text-embedding-3-small"
    WINDOW_SECONDS: float = 30.0
    WINDOW_STRIDE_SECONDS: float = 15.0
    DEDUP_COSINE_THRESHOLD: float = 0.85
