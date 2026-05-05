from uuid import UUID

import structlog
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.chat.constants import (
    CHAT_RETRIEVAL_GRAPH_TYPES,
    ChatScope,
    GraphHit,
    RetrievedContext,
    UtteranceHit,
)
from app.chat.models import UtteranceEmbedding
from app.config import config
from app.core.client import get_ai_client
from app.graph.constants import NodeType
from app.graph.models import GraphNode
from app.meeting.constants import MeetingStatus
from app.meeting.models import Meeting
from app.participant.models import Participant
from app.transcript.models import Utterance

logger = structlog.get_logger()


class ChatRetriever:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def retrieve(
        self,
        query: str,
        scope: ChatScope,
        meeting_id: UUID | None,
    ) -> RetrievedContext:
        ai_client = get_ai_client()
        vectors = await ai_client.embed([query])
        if not vectors:
            return RetrievedContext(utterances=[], graph_nodes=[])

        query_vec = vectors[0]
        utterance_top_k = (
            config.chat.UTTERANCE_TOP_K_MEETING if scope == ChatScope.MEETING else config.chat.UTTERANCE_TOP_K_ALL
        )
        utterances = await self._search_utterances(query_vec, scope, meeting_id, utterance_top_k)
        graph_nodes = await self._search_graph(query_vec, scope, meeting_id, config.chat.GRAPH_TOP_K)
        logger.debug(
            "chat retrieval done",
            scope=scope,
            meeting_id=meeting_id,
            utterance_hits=len(utterances),
            graph_hits=len(graph_nodes),
        )
        return RetrievedContext(utterances=utterances, graph_nodes=graph_nodes)

    async def _search_utterances(
        self,
        query_vec: list[float],
        scope: ChatScope,
        meeting_id: UUID | None,
        top_k: int,
    ) -> list[UtteranceHit]:
        distance = col(UtteranceEmbedding.embedding).cosine_distance(query_vec)
        stmt = (
            select(
                Utterance,
                Meeting.title,
                Meeting.started_at,
                Participant.name,
                distance,
            )
            .join(UtteranceEmbedding, col(UtteranceEmbedding.utterance_id) == col(Utterance.id))
            .join(Meeting, col(Meeting.id) == col(Utterance.meeting_id))
            .join(Participant, col(Participant.id) == col(Utterance.participant_id), isouter=True)
            .where(col(Meeting.status) == MeetingStatus.FINAL)
            .where(col(Utterance.text) != "")
            .order_by(distance)
            .limit(top_k)
        )
        if scope == ChatScope.MEETING and meeting_id:
            stmt = stmt.where(col(Utterance.meeting_id) == meeting_id)

        rows = (await self.session.exec(stmt)).all()
        hits: list[UtteranceHit] = []
        for index, row in enumerate(rows, start=1):
            utt, m_title, m_started, speaker, dist = row
            hits.append(
                UtteranceHit(
                    ref=f"u{index}",
                    utterance_id=utt.id,
                    meeting_id=utt.meeting_id,
                    meeting_title=m_title,
                    meeting_started_at=m_started,
                    speaker=speaker,
                    t_start=utt.t_start,
                    t_end=utt.t_end,
                    text=utt.text,
                    score=1.0 - float(dist),
                )
            )
        return hits

    async def _search_graph(
        self,
        query_vec: list[float],
        scope: ChatScope,
        meeting_id: UUID | None,
        top_k: int,
    ) -> list[GraphHit]:
        types = [NodeType(t) for t in CHAT_RETRIEVAL_GRAPH_TYPES]
        distance = col(GraphNode.embedding).cosine_distance(query_vec)
        stmt = (
            select(GraphNode, Meeting.title, Meeting.started_at, distance)
            .join(Meeting, col(Meeting.id) == col(GraphNode.meeting_id))
            .where(col(GraphNode.type).in_(types))
            .where(col(GraphNode.embedding).is_not(None))
            .where(col(Meeting.status) == MeetingStatus.FINAL)
            .order_by(distance)
            .limit(top_k)
        )
        if scope == ChatScope.MEETING and meeting_id:
            stmt = stmt.where(col(GraphNode.meeting_id) == meeting_id)

        rows = (await self.session.exec(stmt)).all()
        hits: list[GraphHit] = []
        for index, row in enumerate(rows, start=1):
            node, m_title, m_started, dist = row
            text = self._node_text(node.fields)
            if not text:
                continue

            hits.append(
                GraphHit(
                    ref=f"g{index}",
                    node_id=node.id,
                    meeting_id=node.meeting_id,
                    meeting_title=m_title,
                    meeting_started_at=m_started,
                    type=str(node.type),
                    text=text,
                    score=1.0 - float(dist),
                )
            )
        return hits

    @staticmethod
    def _node_text(fields: dict) -> str:
        for key in ("text", "title", "summary", "name"):
            value = fields.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return ""
