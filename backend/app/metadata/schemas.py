from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.core.base_schema import BaseSchema
from app.graph.constants import NodeStatus

SUMMARY_MIN_WORDS = 5
SUMMARY_MAX_WORDS = 25


class ExtractedTopic(BaseSchema):
    temp_id: str
    title: str
    summary: str | None = None


class ExtractedDecision(BaseSchema):
    temp_id: str
    text: str
    status: NodeStatus = NodeStatus.PROVISIONAL
    source_utterance_refs: list[str] = Field(min_length=1)
    topic_refs: list[str] = Field(default_factory=list)
    decided_by_person_ref: str | None = None


class ExtractedActionItem(BaseSchema):
    temp_id: str
    text: str
    due_date: str | None = None
    status: NodeStatus = NodeStatus.PROVISIONAL
    source_utterance_refs: list[str] = Field(min_length=1)
    topic_refs: list[str] = Field(default_factory=list)
    assignee_person_ref: str | None = None


class ExtractedOpenQuestion(BaseSchema):
    temp_id: str
    text: str
    status: NodeStatus = NodeStatus.PROVISIONAL
    source_utterance_refs: list[str] = Field(min_length=1)
    topic_refs: list[str] = Field(default_factory=list)


class ExtractedMetadata(BaseSchema):
    summary: str
    topics: list[ExtractedTopic] = Field(default_factory=list)
    decisions: list[ExtractedDecision] = Field(default_factory=list)
    action_items: list[ExtractedActionItem] = Field(default_factory=list)
    open_questions: list[ExtractedOpenQuestion] = Field(default_factory=list)

    @field_validator("summary")
    @classmethod
    def _check_summary_word_count(cls, value: str) -> str:
        words = value.split()
        if not (SUMMARY_MIN_WORDS <= len(words) <= SUMMARY_MAX_WORDS):
            raise ValueError(f"summary must be {SUMMARY_MIN_WORDS}-{SUMMARY_MAX_WORDS} words, got {len(words)}")
        return value


class DecisionProjection(BaseSchema):
    id: UUID
    text: str
    status: NodeStatus
    owner_name: str | None
    source_t_start: float | None
    source_utterance_id: UUID | None
    topic_ids: list[UUID]


class ActionItemProjection(BaseSchema):
    id: UUID
    text: str
    status: NodeStatus
    due_date: str | None
    owner_name: str | None
    source_t_start: float | None
    source_utterance_id: UUID | None
    topic_ids: list[UUID]


class OpenQuestionProjection(BaseSchema):
    id: UUID
    text: str
    status: NodeStatus
    source_t_start: float | None
    source_utterance_id: UUID | None
    topic_ids: list[UUID]


class TopicProjection(BaseSchema):
    id: UUID
    name: str
    summary: str | None
    relates_previous: bool


class RelatedMeetingProjection(BaseSchema):
    id: UUID
    title: str
    started_at: datetime
    shared_topic_names: list[str]


class MeetingMetadataResponse(BaseSchema):
    meeting_id: UUID
    summary: str | None
    metadata_generated_at: datetime | None
    decisions: list[DecisionProjection]
    action_items: list[ActionItemProjection]
    open_questions: list[OpenQuestionProjection]
    topics: list[TopicProjection]
    related_meetings: list[RelatedMeetingProjection]
