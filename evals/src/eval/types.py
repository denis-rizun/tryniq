"""Wire types shared between the runner (parent) and adapter scripts (subprocess)."""

from pydantic import BaseModel, Field


class Word(BaseModel):
    word: str
    start: float
    end: float
    prob: float | None = None


class Segment(BaseModel):
    t_start: float
    t_end: float
    text: str
    speaker: str | None = None
    words: list[Word] = Field(default_factory=list)


class Partial(BaseModel):
    """One partial-hypothesis emission from a live adapter.

    ``audio_t_end_s`` is the audio-timeline position the partial covers up to.
    ``wall_offset_ms`` is wall-clock ms since the adapter started consuming audio
    (i.e. since the audio's t=0). For real-time-paced adapters this lets the
    runner compute ``user_perceived_latency_ms = wall_offset_ms - audio_t_end_s*1000``.
    """

    text: str
    audio_t_end_s: float
    wall_offset_ms: float
    is_final: bool = False


class Hypothesis(BaseModel):
    """One adapter run on one audio file. Always emitted as JSON on adapter stdout."""

    text: str
    segments: list[Segment] = Field(default_factory=list)
    # Live-only: per-chunk partial-hypothesis trace. Used to compute streaming metrics
    # (stability ratio, median rewrite distance) and audio-timeline-relative latency.
    partials: list[Partial] = Field(default_factory=list)
    # Latency metrics (live-only; None for offline adapters).
    time_to_first_partial_ms: float | None = None
    partial_to_final_lag_ms: float | None = None
    # Filled by the runner, not the adapter.
    audio_duration_s: float | None = None
    wall_clock_s: float | None = None
    peak_rss_mb: float | None = None


class AdapterError(BaseModel):
    error: str
    detail: str | None = None
