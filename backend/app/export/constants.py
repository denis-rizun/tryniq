from enum import StrEnum

MEDIA_TYPE = "text/markdown; charset=utf-8"


class SectionId(StrEnum):
    TRANSCRIPT = "transcript"
    SUMMARY = "summary"
    DECISIONS = "decisions"
    ACTIONS = "actions"
    QUESTIONS = "questions"
    TOPICS = "topics"
    GRAPH = "graph"
    SPEAKERS = "speakers"
    TIMINGS = "timings"
    CONFIDENCE = "confidence"


DEFAULT_SECTIONS: frozenset[SectionId] = frozenset(
    {
        SectionId.SUMMARY,
        SectionId.DECISIONS,
        SectionId.ACTIONS,
        SectionId.QUESTIONS,
        SectionId.TOPICS,
        SectionId.GRAPH,
        SectionId.SPEAKERS,
        SectionId.TRANSCRIPT,
        SectionId.TIMINGS,
    }
)
