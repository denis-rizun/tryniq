import os
import tempfile
from threading import Lock
from typing import Any

import structlog

from app.asr.interface import ASRClient
from app.asr.types import AsrSegment, WordTiming
from app.config import config

logger = structlog.get_logger()


class ParakeetMlxClient(ASRClient):
    def __init__(self) -> None:
        self._model = None
        self._lock = Lock()

    def _ensure_model(self) -> Any:
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is not None:
                return self._model
            from parakeet_mlx import from_pretrained

            logger.info("loading parakeet-mlx model", model=config.asr.MODEL)
            self._model = from_pretrained(config.asr.MODEL)
        return self._model

    def transcribe(self, wav_bytes: bytes) -> list[AsrSegment]:
        model = self._ensure_model()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_bytes)
            tmp_path = f.name

        try:
            result = model.transcribe(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        sentences = getattr(result, "sentences", None)
        segments: list[AsrSegment] = []
        if sentences:
            for sent in sentences:
                words = [
                    WordTiming(
                        word=w.text,
                        start=float(w.start),
                        end=float(w.end),
                        confidence=None,
                    )
                    for w in getattr(sent, "tokens", [])
                ]
                segments.append(
                    AsrSegment(
                        t_start=float(sent.start),
                        t_end=float(sent.end),
                        text=sent.text.strip(),
                        confidence=None,
                        words=words,
                    )
                )
            return segments

        tokens = getattr(result, "tokens", []) or []
        words = [WordTiming(word=t.text, start=float(t.start), end=float(t.end)) for t in tokens]
        text = (getattr(result, "text", "") or "").strip()
        if not text and not words:
            return []

        t_start = words[0].start if words else 0.0
        t_end = words[-1].end if words else 0.0
        return [AsrSegment(t_start=t_start, t_end=t_end, text=text, confidence=None, words=words)]

    @property
    def model_name(self) -> str:
        return f"parakeet-mlx:{config.asr.MODEL}"
