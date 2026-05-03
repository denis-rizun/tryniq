from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import BASE_MODEL_CONFIG


class ASRSettings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_MODEL_CONFIG, env_prefix="ASR_")

    LIVE_ENABLED: bool = True
    LIVE_PROVIDER: Literal["fluid_audio"] = "fluid_audio"
    LIVE_MODEL: Literal["parakeet-tdt-v2"] = "parakeet-tdt-v2"
    LIVE_IDLE_TIMEOUT_S: int = 120
    LIVE_AUTH_TOKEN: SecretStr = SecretStr("")

    FINAL_PROVIDER: Literal["faster_whisper"] = "faster_whisper"
    FINAL_MODEL: Literal["large-v3-turbo"] = "large-v3-turbo"
    FINAL_DEVICE: str = "cpu"
    FINAL_COMPUTE_TYPE: str = "int8"
    FINAL_LANGUAGE: str = "en"
    FINAL_INITIAL_PROMPT: str = (
        "Tryniq, MinIO, TaskIQ, faster-whisper, large-v3-turbo, Postgres, pgvector, "
        "Redis, Next.js, FastAPI, Moonshine, Silero, Anthropic, Claude, Ollama, "
        "Qwen, Whisper, ECAPA, WebRTC, AudioWorklet, SQLModel, Alembic."
    )

    @property
    def final_asr_id(self) -> str:
        return f"{self.FINAL_PROVIDER}-{self.FINAL_MODEL}"

    @property
    def live_asr_id(self) -> str:
        return f"{self.LIVE_PROVIDER}-{self.LIVE_MODEL}"
