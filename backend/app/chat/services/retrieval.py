from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import structlog
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.chat.constants import ChatScope
from app.chat.models import UtteranceEmbedding
from app.chat.services.graph_hits import GraphHit, GraphHitBuilder
from app.config import config
from app.core.client import get_ai_client
from app.graph.constants import EdgeType, NodeType
from app.graph.models import GraphEdge, GraphNode
from app.meeting.constants import MeetingStatus
from app.meeting.models import Meeting
from app.participant.models import Participant
from app.transcript.models import Utterance

logger = structlog.get_logger()


@dataclass(slots=True)
class UtteranceHit:
    ref: str
    utterance_id: UUID
    meeting_id: UUID
    meeting_title: str | None
    meeting_started_at: datetime | None
    speaker: str | None
    t_start: float
    t_end: float
    text: str
    score: float


@dataclass(slots=True)
class RetrievedContext:
    utterances: list[UtteranceHit]
    graph_nodes: list[GraphHit]

    def is_empty(self) -> bool:
        return not self.utterances and not self.graph_nodes


class ChatRetriever:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._graph_hits = GraphHitBuilder(session)

    async def retrieve(self, query: str, scope: ChatScope, meeting_id: UUID | None) -> RetrievedContext:
        vectors = await get_ai_client().embed([query])
        query_vector = vectors[0] if vectors else None

        if scope == ChatScope.MEETING and meeting_id:
            utterances = await self._load_meeting_transcript(meeting_id)
            graph_nodes = await self._graph_hits.load_meeting_graph(meeting_id)
        elif query_vector is None:
            utterances = []
            graph_nodes = []
        else:
            utterances = await self._search_utterances(query_vector, scope, meeting_id, config.chat.UTTERANCE_TOP_K_ALL)
            graph_nodes = await self._graph_hits.search_all(query, query_vector, config.chat.GRAPH_TOP_K_ALL)
            source_utterances = await self._load_source_utterances([hit.node_id for hit in graph_nodes])
            utterances = self._merge_utterances(utterances, source_utterances)

        logger.debug(
            "chat retrieval done",
            scope=scope,
            meeting_id=meeting_id,
            utterance_hits=len(utterances),
            graph_hits=len(graph_nodes),
        )
        return RetrievedContext(utterances=utterances, graph_nodes=graph_nodes)

    async def _load_meeting_transcript(self, meeting_id: UUID) -> list[UtteranceHit]:
        statement = (
            select(Utterance, Meeting.title, Meeting.started_at, Participant.name)
            .join(Meeting, col(Meeting.id) == col(Utterance.meeting_id))
            .join(Participant, col(Participant.id) == col(Utterance.participant_id), isouter=True)
            .where(col(Utterance.meeting_id) == meeting_id)
            .where(col(Utterance.text) != "")
            .where(col(Utterance.is_final).is_(True))
            .order_by(col(Utterance.t_start))
        )
        rows = (await self._session.exec(statement)).all()
        return [
            UtteranceHit(
                ref=f"u{index}",
                utterance_id=utterance.id,
                meeting_id=utterance.meeting_id,
                meeting_title=title,
                meeting_started_at=started_at,
                speaker=speaker,
                t_start=utterance.t_start,
                t_end=utterance.t_end,
                text=utterance.text,
                score=1.0,
            )
            for index, (utterance, title, started_at, speaker) in enumerate(rows, start=1)
        ]

    async def _load_source_utterances(self, grounded_node_ids: list[UUID]) -> list[UtteranceHit]:
        if not grounded_node_ids:
            return []

        edge_statement = (
            select(GraphNode.fields)
            .join(GraphEdge, col(GraphEdge.to_id) == col(GraphNode.id))
            .where(col(GraphEdge.type) == EdgeType.SOURCE)
            .where(col(GraphEdge.from_id).in_(grounded_node_ids))
            .where(col(GraphNode.type) == NodeType.UTTERANCE)
        )
        utterance_ids: set[UUID] = set()
        for fields in (await self._session.exec(edge_statement)).all():
            raw_id = (fields or {}).get("utterance_id")
            if not raw_id:
                continue

            try:
                utterance_ids.add(UUID(str(raw_id)))
            except ValueError:
                continue

        if not utterance_ids:
            return []

        statement = (
            select(Utterance, Meeting.title, Meeting.started_at, Participant.name)
            .join(Meeting, col(Meeting.id) == col(Utterance.meeting_id))
            .join(Participant, col(Participant.id) == col(Utterance.participant_id), isouter=True)
            .where(col(Utterance.id).in_(utterance_ids))
            .where(col(Utterance.text) != "")
        )
        rows = (await self._session.exec(statement)).all()
        return [
            UtteranceHit(
                ref="",
                utterance_id=utterance.id,
                meeting_id=utterance.meeting_id,
                meeting_title=title,
                meeting_started_at=started_at,
                speaker=speaker,
                t_start=utterance.t_start,
                t_end=utterance.t_end,
                text=utterance.text,
                score=1.0,
            )
            for utterance, title, started_at, speaker in rows
        ]

    async def _search_utterances(
        self,
        query_vector: list[float],
        scope: ChatScope,
        meeting_id: UUID | None,
        top_k: int,
    ) -> list[UtteranceHit]:
        distance = col(UtteranceEmbedding.embedding).cosine_distance(query_vector)
        statement = (
            select(Utterance, Meeting.title, Meeting.started_at, Participant.name, distance)
            .join(UtteranceEmbedding, col(UtteranceEmbedding.utterance_id) == col(Utterance.id))
            .join(Meeting, col(Meeting.id) == col(Utterance.meeting_id))
            .join(Participant, col(Participant.id) == col(Utterance.participant_id), isouter=True)
            .where(col(Meeting.status) == MeetingStatus.FINAL)
            .where(col(Utterance.text) != "")
            .order_by(distance)
            .limit(top_k)
        )
        if scope == ChatScope.MEETING and meeting_id:
            statement = statement.where(col(Utterance.meeting_id) == meeting_id)

        rows = (await self._session.exec(statement)).all()
        return [
            UtteranceHit(
                ref=f"u{index}",
                utterance_id=utterance.id,
                meeting_id=utterance.meeting_id,
                meeting_title=title,
                meeting_started_at=started_at,
                speaker=speaker,
                t_start=utterance.t_start,
                t_end=utterance.t_end,
                text=utterance.text,
                score=1.0 - float(distance_value),
            )
            for index, (utterance, title, started_at, speaker, distance_value) in enumerate(rows, start=1)
        ]

    @staticmethod
    def _merge_utterances(primary: list[UtteranceHit], extra: list[UtteranceHit]) -> list[UtteranceHit]:
        seen_ids = {hit.utterance_id for hit in primary}
        merged = list(primary)
        for hit in extra:
            if hit.utterance_id not in seen_ids:
                seen_ids.add(hit.utterance_id)
                merged.append(hit)
        for index, hit in enumerate(merged, start=1):
            hit.ref = f"u{index}"
        return merged
