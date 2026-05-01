from pathlib import Path

from pydantic_settings import SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
BASE_MODEL_CONFIG = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore", env_file_encoding="utf-8")
