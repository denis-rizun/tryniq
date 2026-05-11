from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import BASE_MODEL_CONFIG


class ChatSettings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_MODEL_CONFIG, env_prefix="CHAT_")

    LLM_MODEL: str = "gpt-5.5"
    MAX_HISTORY: int = 10
    UTTERANCE_TOP_K_MEETING: int = 8
    UTTERANCE_TOP_K_ALL: int = 30
    GRAPH_TOP_K: int = 4
    GRAPH_TOP_K_ALL: int = 12
    MAX_OUTPUT_TOKENS: int = 1024
    EMBED_BATCH_SIZE: int = 64
