import asyncio
from dataclasses import dataclass, field
from uuid import UUID


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
        return [[w.word, w.start, w.end, w.confidence] for w in self.words]


@dataclass
class StreamState:
    stream_id: UUID
    meeting_id: UUID
    stream_idx: int
    participant_id: UUID | None
    audio_queue: asyncio.Queue[bytes | None]
    seq: int = 0
    audio_chunks_dropped: int = 0
    last_drop_warn_at: float = 0.0
    last_partial_text: str = ""
    sender_task: asyncio.Task[None] | None = None
    closed: bool = False
