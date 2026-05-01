from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import BASE_MODEL_CONFIG


# asr = active speaker recognition
class ASRSettings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_MODEL_CONFIG, env_prefix="ASR_")

    PROVIDER: Literal["faster_whisper", "parakeet_mlx"] = "faster_whisper"
    MODEL: str = "large-v3-turbo"
    DEVICE: str = "cpu"
    COMPUTE_TYPE: str = "int8"
    LANGUAGE: str = "en"
    INITIAL_PROMPT: str = (
        "Tryniq, MinIO, TaskIQ, faster-whisper, large-v3-turbo, Postgres, pgvector, "
        "Redis, Next.js, FastAPI, Moonshine, Silero, Anthropic, Claude, Ollama, "
        "Qwen, Whisper, ECAPA, WebRTC, AudioWorklet, SQLModel, Alembic."
    )
