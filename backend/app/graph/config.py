from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import BASE_MODEL_CONFIG


class GraphSettings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_MODEL_CONFIG, env_prefix="GRAPH_")

    LLM_MODEL: str = "gpt-4o-mini"
    LLM_MAX_TOKENS: int = 16384
    WINDOW_SECONDS: float = 30.0
    WINDOW_STRIDE_SECONDS: float = 15.0
    DEDUP_COSINE_THRESHOLD: float = 0.85
