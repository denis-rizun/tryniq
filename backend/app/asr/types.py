from dataclasses import dataclass, field


@dataclass
class WordTiming:
    word: str
    start: float
    end: float
    confidence: float | None = None


@dataclass
class AsrSegment:
    t_start: float
    t_end: float
    text: str
    confidence: float | None = None
    words: list[WordTiming] = field(default_factory=list)

    def words_as_jsonable(self) -> list[list]:
        return [[w.word, w.start, w.end, w.confidence] for w in self.words]
