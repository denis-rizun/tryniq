from datetime import datetime
from typing import Literal
from uuid import UUID

from app.core.base_schema import BaseSchema
from app.meeting.constants import MeetingStatus


class MeetingSearchResponse(BaseSchema):
    id: UUID
    type: Literal["meeting"] = "meeting"
    title: str
    summary: str | None
    status: MeetingStatus
    started_at: datetime
    url: str


class PersonSearchResponse(BaseSchema):
    id: UUID
    type: Literal["person"] = "person"
    name: str
    is_local_user: bool
    meeting_count: int
    url: str


class UtteranceSearchResponse(BaseSchema):
    id: UUID
    type: Literal["utterance"] = "utterance"
    text: str
    speaker_name: str | None
    meeting_id: UUID
    meeting_title: str
    t_start: float
    url: str


class SearchResults(BaseSchema):
    meetings: list[MeetingSearchResponse] = []
    people: list[PersonSearchResponse] = []
    utterances: list[UtteranceSearchResponse] = []


class SearchTotals(BaseSchema):
    meetings: int = 0
    people: int = 0
    utterances: int = 0


class SearchResponse(BaseSchema):
    query: str
    results: SearchResults
    total: SearchTotals
