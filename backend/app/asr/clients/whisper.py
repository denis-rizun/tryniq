import io
import math
from threading import Lock
from typing import Any

import structlog

from app.asr.interface import ASRClient
from app.asr.types import AsrSegment, WordTiming
from app.config import config

logger = structlog.get_logger()


class FasterWhisperClient(ASRClient):
    def __init__(self) -> None:
        self._model = None
        self._lock = Lock()

    def _ensure_model(self) -> Any:
        if self._model is not None:
            return self._model

        with self._lock:
            if self._model is not None:
                return self._model

            from faster_whisper import WhisperModel

            logger.info(
                "loading faster-whisper model",
                model=config.asr.MODEL,
                device=config.asr.DEVICE,
                compute_type=config.asr.COMPUTE_TYPE,
            )
            self._model = WhisperModel(
                config.asr.MODEL,
                device=config.asr.DEVICE,
                compute_type=config.asr.COMPUTE_TYPE,
            )
        return self._model

    def transcribe(self, wav_bytes: bytes) -> list[AsrSegment]:
        model = self._ensure_model()
        segments_iter, _ = model.transcribe(
            io.BytesIO(wav_bytes),
            language=config.asr.LANGUAGE,
            word_timestamps=True,
            vad_filter=False,
            beam_size=5,
            initial_prompt=config.asr.INITIAL_PROMPT,
        )

        segments: list[AsrSegment] = []
        for seg in segments_iter:
            words: list[WordTiming] = []
            if seg.words:
                for w in seg.words:
                    words.append(
                        WordTiming(
                            word=w.word,
                            start=float(w.start) if w.start is not None else float(seg.start),
                            end=float(w.end) if w.end is not None else float(seg.end),
                            confidence=float(w.probability) if w.probability is not None else None,
                        )
                    )

            confidence: float | None = None
            if seg.avg_logprob is not None:
                confidence = math.exp(seg.avg_logprob)

            segments.append(
                AsrSegment(
                    t_start=float(seg.start),
                    t_end=float(seg.end),
                    text=seg.text.strip(),
                    confidence=confidence,
                    words=words,
                )
            )
        return segments

    @property
    def model_name(self) -> str:
        return f"faster-whisper-{config.asr.MODEL}"
