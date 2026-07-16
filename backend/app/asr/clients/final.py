import io
import math
from dataclasses import dataclass, field
from functools import lru_cache
from threading import Lock
from typing import Any

import structlog

from app.config import config

logger = structlog.get_logger()


@dataclass
class WordTiming:
    word: str
    start: float
    end: float
    confidence: float | None = None


@dataclass
class ASRSegment:
    t_start: float
    t_end: float
    text: str
    confidence: float | None = None
    words: list[WordTiming] = field(default_factory=list)

    def words_as_jsonable(self) -> list[list]:
        return [[word.word, word.start, word.end, word.confidence] for word in self.words]


class FasterWhisperClient:
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
                model=config.asr.FINAL_MODEL,
                device=config.asr.FINAL_DEVICE,
                compute_type=config.asr.FINAL_COMPUTE_TYPE,
            )
            self._model = WhisperModel(
                config.asr.FINAL_MODEL,
                device=config.asr.FINAL_DEVICE,
                compute_type=config.asr.FINAL_COMPUTE_TYPE,
            )
        return self._model

    def transcribe(self, audio: str | bytes) -> list[ASRSegment]:
        model = self._ensure_model()
        source = audio if isinstance(audio, str) else io.BytesIO(audio)
        segments_iter, _ = model.transcribe(
            source,
            language=config.asr.FINAL_LANGUAGE,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500, "speech_pad_ms": 200},
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6,
            compression_ratio_threshold=2.4,
            condition_on_previous_text=False,
            beam_size=5,
            initial_prompt=config.asr.FINAL_INITIAL_PROMPT,
        )

        segments: list[ASRSegment] = []
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

            for chunk in self._split_on_word_gaps(words):
                chunk = self._strip_low_confidence_edges(chunk)
                if not chunk:
                    continue

                text = "".join(w.word for w in chunk).strip()
                if not text:
                    continue

                if confidence is not None and confidence < 0.35 and len(text) <= 8:
                    continue

                segments.append(
                    ASRSegment(
                        t_start=chunk[0].start,
                        t_end=chunk[-1].end,
                        text=text,
                        confidence=confidence,
                        words=chunk,
                    )
                )
        return segments

    @staticmethod
    def _split_on_word_gaps(words: list[WordTiming]) -> list[list[WordTiming]]:
        max_gap_seconds = 1.5
        if not words:
            return []
        chunks: list[list[WordTiming]] = [[words[0]]]
        for previous, current in zip(words, words[1:], strict=False):
            if current.start - previous.end > max_gap_seconds:
                chunks.append([current])
            else:
                chunks[-1].append(current)
        return chunks

    @staticmethod
    def _strip_low_confidence_edges(words: list[WordTiming]) -> list[WordTiming]:
        threshold = 0.35
        start = 0
        while start < len(words) and (words[start].confidence or 1.0) < threshold:
            start += 1
        end = len(words)
        while end > start and (words[end - 1].confidence or 1.0) < threshold:
            end -= 1
        return words[start:end]


@lru_cache(maxsize=1)
def get_faster_whisper_client() -> FasterWhisperClient:
    return FasterWhisperClient()
