from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import BASE_MODEL_CONFIG


class MetadataSettings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_MODEL_CONFIG, env_prefix="METADATA_")

    LLM_MODEL: str = "gpt-5.5"
    LLM_MAX_TOKENS: int = 16384
