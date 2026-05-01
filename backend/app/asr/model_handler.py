from app.asr.clients.parakeet import ParakeetMlxClient
from app.asr.clients.whisper import FasterWhisperClient
from app.asr.interface import ASRClient
from app.config import config


def get_asr_model() -> ASRClient:
    if config.asr.PROVIDER == "faster_whisper":
        return FasterWhisperClient()
    return ParakeetMlxClient()
