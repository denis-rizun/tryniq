from abc import ABC, abstractmethod

from app.asr.types import AsrSegment


class ASRClient(ABC):
    @abstractmethod
    def transcribe(self, wav_bytes: bytes) -> list[AsrSegment]:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass
