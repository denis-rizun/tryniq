from uuid import UUID

from sqlalchemy import bindparam, text
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.meeting.models import Meeting


class RelatedMeetingsFinder:
    SUMMARY_DISTANCE_LIMIT = 0.3
    TOPIC_DISTANCE_LIMIT = 0.15
    MIN_SHARED_TOPICS = 2
    MAX_RESULTS = 5

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def rank(self, meeting_id: UUID, meeting: Meeting) -> list[UUID]:
        if meeting.summary_embedding is None:
            return []

        scores: dict[UUID, float] = {}
        for mid, distance in await self._summary_neighbors(meeting_id, meeting.summary_embedding):
            scores[mid] = max(scores.get(mid, 0.0), 1.0 - distance)

        for mid, shared in await self._shared_topic_counts(meeting_id):
            scores[mid] = max(scores.get(mid, 0.0), min(1.0, shared / 5.0))

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        return [mid for mid, _ in ranked[: self.MAX_RESULTS]]

    async def _summary_neighbors(self, meeting_id: UUID, embedding: list[float]) -> list[tuple[UUID, float]]:
        query = (
            select(
                Meeting.id,
                col(Meeting.summary_embedding).cosine_distance(embedding).label("dist"),
            )
            .where(Meeting.id != meeting_id)
            .where(col(Meeting.summary_embedding).is_not(None))
            .where(col(Meeting.summary_embedding).cosine_distance(embedding) <= self.SUMMARY_DISTANCE_LIMIT)
            .order_by("dist")
            .limit(self.MAX_RESULTS)
        )
        rows = (await self.session.exec(query)).all()
        return [(row[0], float(row[1])) for row in rows]

    async def _shared_topic_counts(self, meeting_id: UUID) -> list[tuple[UUID, int]]:
        query = text(
            """
            SELECT other.meeting_id AS meeting_id, COUNT(DISTINCT this.id) AS shared
            FROM graph_node this
            JOIN graph_node other
              ON other.type = this.type
              AND other.meeting_id <> this.meeting_id
              AND (this.embedding <=> other.embedding) <= :topic_distance
            WHERE this.meeting_id = :meeting_id AND this.type = 'TOPIC'
            GROUP BY other.meeting_id
            HAVING COUNT(DISTINCT this.id) >= :min_shared
            ORDER BY shared DESC
            LIMIT 10
            """
        ).bindparams(
            bindparam("meeting_id", value=str(meeting_id)),
            bindparam("topic_distance", value=self.TOPIC_DISTANCE_LIMIT),
            bindparam("min_shared", value=self.MIN_SHARED_TOPICS),
        )
        rows = (await self.session.exec(query)).all()
        return [(self._coerce_uuid(row[0]), int(row[1])) for row in rows]

    @staticmethod
    def _coerce_uuid(value: object) -> UUID:
        if isinstance(value, UUID):
            return value
        return UUID(str(value))
