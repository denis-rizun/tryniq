from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import BASE_MODEL_CONFIG


class UploadSettings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_MODEL_CONFIG, env_prefix="UPLOAD_")

    MAX_BYTES: int = 2 * 1024 * 1024 * 1024
    MAX_DURATION_SECONDS: float = 4 * 60 * 60.0
    NORMALIZED_SAMPLE_RATE: int = 16000
    NORMALIZED_CHANNELS: int = 1
    DIARIZEN_MODEL: str = "BUT-FIT/diarizen-wavlm-large-s80-md-v2"
