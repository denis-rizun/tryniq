from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import BASE_MODEL_CONFIG


class MinioSettings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_MODEL_CONFIG, env_prefix="MINIO_")

    ENDPOINT_URL: str = ""
    ACCESS_KEY: SecretStr = SecretStr("")
    SECRET_KEY: SecretStr = SecretStr("")
    BUCKET: str = "tryniq"
