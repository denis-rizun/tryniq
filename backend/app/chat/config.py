from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import BASE_MODEL_CONFIG


class ChatSettings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_MODEL_CONFIG, env_prefix="CHAT_")

    OPENAI_API_KEY: SecretStr = SecretStr("")
    LLM_MODEL: str = "gpt-4o-mini"
    EMBED_MODEL: str = "text-embedding-3-small"
    MAX_HISTORY: int = 10
    UTTERANCE_TOP_K_MEETING: int = 8
    UTTERANCE_TOP_K_ALL: int = 12
    GRAPH_TOP_K: int = 4
    MAX_OUTPUT_TOKENS: int = 1024
    EMBED_BATCH_SIZE: int = 64
    LANGFUSE_ENABLED: bool = False
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"
    LANGFUSE_PUBLIC_KEY: SecretStr = SecretStr("")
    LANGFUSE_SECRET_KEY: SecretStr = SecretStr("")
