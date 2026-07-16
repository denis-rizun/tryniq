from typing import Any
from uuid import UUID

from sqlalchemy import String, cast, func, literal_column
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.meeting.models import Meeting
from app.participant.models import Participant
from app.search.constants import ALL_TYPES
from app.search.schemas import (
    MeetingSearchResponse,
    PersonSearchResponse,
    SearchResponse,
    SearchResults,
    SearchTotals,
    UtteranceSearchResponse,
)
from app.transcript.models import Utterance


class SearchService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(self, query: str, limit: int, types: str | None) -> SearchResponse:
        requested_types = {part.strip() for part in types.split(",")} & ALL_TYPES if types else set(ALL_TYPES)
        results = SearchResults()
        totals = SearchTotals()

        if "meetings" in requested_types:
            results.meetings, totals.meetings = await self._search_meetings(query, limit)
        if "people" in requested_types:
            results.people, totals.people = await self._search_people(query, limit)
        if "utterances" in requested_types:
            results.utterances, totals.utterances = await self._search_utterances(query, limit)

        return SearchResponse(query=query, results=results, total=totals)

    async def _search_meetings(self, query: str, limit: int) -> tuple[list[MeetingSearchResponse], int]:
        tsq = self._tsquery(query)
        weighted_tsv = (
            func.setweight(
                func.to_tsvector("english", func.coalesce(col(Meeting.title), "")),
                literal_column("'A'"),
            )
            .op("||")(
                func.setweight(
                    func.to_tsvector("english", func.coalesce(col(Meeting.summary), "")),
                    literal_column("'B'"),
                )
            )
            .op("||")(
                func.setweight(
                    func.to_tsvector("english", func.coalesce(cast(col(Meeting.status), String), "")),
                    literal_column("'C'"),
                )
            )
        )
        rank = func.ts_rank(weighted_tsv, tsq).label("rank")
        total_over = func.count(literal_column("1")).over().label("total")

        stmt = (
            select(Meeting, rank, total_over)
            .where(weighted_tsv.op("@@")(tsq))
            .order_by(rank.desc(), col(Meeting.started_at).desc())
            .limit(limit)
        )
        rows = (await self.session.exec(stmt)).all()
        if not rows:
            return [], 0

        total = rows[0][-1]
        items = [
            MeetingSearchResponse(
                id=meeting.id,
                title=meeting.title,
                summary=meeting.summary,
                status=meeting.status,
                started_at=meeting.started_at,
                url=f"/meetings/{meeting.id}/overview",
            )
            for meeting, _rank, _total in rows
        ]
        return items, total

    async def _search_people(self, query: str, limit: int) -> tuple[list[PersonSearchResponse], int]:
        tsq = self._tsquery(query)
        tsv = func.to_tsvector("simple", func.coalesce(col(Participant.name), ""))
        rank = func.max(func.ts_rank(tsv, tsq)).label("rank")
        total_over = func.count(literal_column("1")).over().label("total")

        stmt = (
            select(  # type: ignore[call-overload]
                col(Participant.name).label("name"),
                func.bool_or(col(Participant.is_local_user)).label("is_local_user"),
                func.count(func.distinct(col(Participant.meeting_id))).label("meeting_count"),
                cast(func.min(cast(col(Participant.id), String)), String).label("any_participant_id"),
                rank,
                total_over,
            )
            .where(tsv.op("@@")(tsq))
            .group_by(col(Participant.name))
            .order_by(rank.desc(), col(Participant.name))
            .limit(limit)
        )
        rows = (await self.session.exec(stmt)).all()
        if not rows:
            return [], 0

        total = rows[0][-1]
        items = [
            PersonSearchResponse(
                id=UUID(any_participant_id),
                name=name,
                is_local_user=bool(is_local_user),
                meeting_count=int(meeting_count),
                url="/people",
            )
            for name, is_local_user, meeting_count, any_participant_id, _rank, _total in rows
        ]
        return items, total

    async def _search_utterances(self, query: str, limit: int) -> tuple[list[UtteranceSearchResponse], int]:
        tsq = self._tsquery(query)
        weighted_tsv = func.setweight(
            func.to_tsvector("english", func.coalesce(col(Utterance.text), "")),
            literal_column("'A'"),
        ).op("||")(
            func.setweight(
                func.to_tsvector("english", func.coalesce(col(Meeting.title), "")),
                literal_column("'C'"),
            )
        )
        rank = func.ts_rank(weighted_tsv, tsq).label("rank")
        total_over = func.count(literal_column("1")).over().label("total")

        stmt = (
            select(  # type: ignore[call-overload]
                Utterance,
                col(Meeting.title).label("meeting_title"),
                col(Participant.name).label("speaker_name"),
                rank,
                total_over,
            )
            .join(Meeting, col(Meeting.id) == col(Utterance.meeting_id))
            .outerjoin(Participant, col(Participant.id) == col(Utterance.participant_id))
            .where(col(Utterance.is_final).is_(True))
            .where(weighted_tsv.op("@@")(tsq))
            .order_by(rank.desc(), col(Utterance.t_start).desc())
            .limit(limit)
        )
        rows = (await self.session.exec(stmt)).all()
        if not rows:
            return [], 0

        total = rows[0][-1]
        items = [
            UtteranceSearchResponse(
                id=utt.id,
                text=utt.text,
                speaker_name=speaker_name,
                meeting_id=utt.meeting_id,
                meeting_title=meeting_title,
                t_start=utt.t_start,
                url=f"/meetings/{utt.meeting_id}/overview?cite={utt.t_start}",
            )
            for utt, meeting_title, speaker_name, _rank, _total in rows
        ]
        return items, total

    @staticmethod
    def _tsquery(query: str) -> ColumnElement[Any]:
        return func.plainto_tsquery("english", query)
