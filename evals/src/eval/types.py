
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

    text: str
    audio_t_end_s: float
    wall_offset_ms: float
    is_final: bool = False


class Hypothesis(BaseModel):

    text: str
    segments: list[Segment] = Field(default_factory=list)
                                                                                      
                                                                                     
    partials: list[Partial] = Field(default_factory=list)
                                                             
    time_to_first_partial_ms: float | None = None
    partial_to_final_lag_ms: float | None = None
                                            
    audio_duration_s: float | None = None
    wall_clock_s: float | None = None
    peak_rss_mb: float | None = None


class AdapterError(BaseModel):
    error: str
    detail: str | None = None
