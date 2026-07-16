import logging
from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.asr.config import ASRSettings
from app.chat.config import ChatSettings
from app.core.config import BASE_MODEL_CONFIG
from app.graph.config import GraphSettings
from app.ingest.config import MinioSettings
from app.meeting.config import RedisSettings
from app.metadata.config import MetadataSettings
from app.upload.config import UploadSettings


class APISettings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_MODEL_CONFIG, env_prefix="API_")

    NAME: str = "Wombat Proposals API"
    VERSION: str = "1.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    ALLOWED_HOSTS: list[str] = ["http://localhost:3000"]
    ALLOW_CREDENTIALS: bool = True
    ALLOWED_METHODS: list[str] = ["*"]
    ALLOWED_HEADERS: list[str] = ["*"]


class LoggerSettings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_MODEL_CONFIG, env_prefix="LOGGING_")

    LEVEL: int = 0
    LEVEL_NAME: str = "INFO"

    @model_validator(mode="after")
    def set_level(self) -> Self:
        self.LEVEL = logging.getLevelNamesMapping().get(self.LEVEL_NAME.upper(), logging.INFO)
        return self


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_MODEL_CONFIG, env_prefix="POSTGRES_")

    DATABASE: str = ""
    USER: str = ""
    PASSWORD: SecretStr = SecretStr("")
    HOST: str = ""
    PORT: int = 0
    TEST_URL: str = ""
    POOL_SIZE: int = 20
    MAX_OVERFLOW: int = 200

    def get_url(self, driver: str | None = "asyncpg") -> str:
        driver = f"+{driver}" if driver else ""
        return (
            f"postgresql{driver}://{self.USER}:{self.PASSWORD.get_secret_value()}"
            f"@{self.HOST}:{self.PORT}/{self.DATABASE}"
        )


class AISettings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_MODEL_CONFIG, env_prefix="AI_")

    OPENAI_API_KEY: SecretStr = SecretStr("")
    PROVIDER: Literal["OpenAI"] = "OpenAI"
    EMBED_MODEL: str = "text-embedding-3-small"
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"
    LANGFUSE_PUBLIC_KEY: SecretStr = SecretStr("")
    LANGFUSE_SECRET_KEY: SecretStr = SecretStr("")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_MODEL_CONFIG)

    ENV: Literal["DEV", "PROD"] = "DEV"
    api: APISettings = Field(default_factory=APISettings)
    logging: LoggerSettings = Field(default_factory=LoggerSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    minio: MinioSettings = Field(default_factory=MinioSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    asr: ASRSettings = Field(default_factory=ASRSettings)
    ai: AISettings = Field(default_factory=AISettings)
    graph: GraphSettings = Field(default_factory=GraphSettings)
    metadata: MetadataSettings = Field(default_factory=MetadataSettings)
    chat: ChatSettings = Field(default_factory=ChatSettings)
    upload: UploadSettings = Field(default_factory=UploadSettings)

    @classmethod
    @lru_cache
    def get_instance(cls) -> Self:
        return cls()


config = Settings.get_instance()
