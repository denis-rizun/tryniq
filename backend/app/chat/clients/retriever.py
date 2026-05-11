import re
from uuid import UUID

import structlog
from sqlmodel import col, or_, select
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
from app.graph.constants import EdgeType, NodeStatus, NodeType
from app.graph.models import GraphEdge, GraphNode
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
        query_vec = vectors[0] if vectors else None

        if scope == ChatScope.MEETING and meeting_id:
            utterances = await self._load_meeting_transcript(meeting_id)
            graph_nodes = await self._load_meeting_graph(meeting_id)
        else:
            if query_vec is None:
                utterances = []
                graph_nodes = []
            else:
                utterances = await self._search_utterances(
                    query_vec, scope, meeting_id, config.chat.UTTERANCE_TOP_K_ALL
                )
                graph_nodes = await self._search_graph_all(query, query_vec, config.chat.GRAPH_TOP_K_ALL)
                source_utterances = await self._load_source_utterances([h.node_id for h in graph_nodes])
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
        stmt = (
            select(Utterance, Meeting.title, Meeting.started_at, Participant.name)
            .join(Meeting, col(Meeting.id) == col(Utterance.meeting_id))
            .join(Participant, col(Participant.id) == col(Utterance.participant_id), isouter=True)
            .where(col(Utterance.meeting_id) == meeting_id)
            .where(col(Utterance.text) != "")
            .where(col(Utterance.is_final).is_(True))
            .order_by(col(Utterance.t_start))
        )
        rows = (await self.session.exec(stmt)).all()
        hits: list[UtteranceHit] = []
        for index, (utt, m_title, m_started, speaker) in enumerate(rows, start=1):
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
                    score=1.0,
                )
            )
        return hits

    async def _load_meeting_graph(self, meeting_id: UUID) -> list[GraphHit]:
        types = [NodeType(t) for t in CHAT_RETRIEVAL_GRAPH_TYPES]
        stmt = (
            select(GraphNode, Meeting.title, Meeting.started_at)
            .join(Meeting, col(Meeting.id) == col(GraphNode.meeting_id))
            .where(col(GraphNode.meeting_id) == meeting_id)
            .where(col(GraphNode.type).in_(types))
        )
        rows = (await self.session.exec(stmt)).all()
        return await self._build_graph_hits([(node, m_title, m_started) for node, m_title, m_started in rows])

    async def _search_graph_all(self, query: str, query_vec: list[float], top_k: int) -> list[GraphHit]:
        types = [NodeType(t) for t in CHAT_RETRIEVAL_GRAPH_TYPES]
        distance = col(GraphNode.embedding).cosine_distance(query_vec)
        similar_stmt = (
            select(GraphNode, Meeting.title, Meeting.started_at)
            .join(Meeting, col(Meeting.id) == col(GraphNode.meeting_id))
            .where(col(GraphNode.type).in_(types))
            .where(col(GraphNode.embedding).is_not(None))
            .where(col(Meeting.status) == MeetingStatus.FINAL)
            .order_by(distance)
            .limit(top_k)
        )
        rows = list((await self.session.exec(similar_stmt)).all())

        boosted_ids = await self._person_boost_node_ids(query)
        if boosted_ids:
            existing = {node.id for node, _, _ in rows}
            extra_ids = [nid for nid in boosted_ids if nid not in existing]
            if extra_ids:
                extra_stmt = (
                    select(GraphNode, Meeting.title, Meeting.started_at)
                    .join(Meeting, col(Meeting.id) == col(GraphNode.meeting_id))
                    .where(col(GraphNode.id).in_(extra_ids))
                    .where(col(Meeting.status) == MeetingStatus.FINAL)
                )
                rows.extend((await self.session.exec(extra_stmt)).all())

        return await self._build_graph_hits([(node, m_title, m_started) for node, m_title, m_started in rows])

    async def _person_boost_node_ids(self, query: str) -> list[UUID]:
        terms = self._extract_name_terms(query)
        if not terms:
            return []

        like_clauses = [col(GraphNode.fields).op("->>")("name").ilike(f"%{t}%") for t in terms]
        person_stmt = select(GraphNode.id).where(col(GraphNode.type) == NodeType.PERSON).where(or_(*like_clauses))
        person_ids = list((await self.session.exec(person_stmt)).all())
        if not person_ids:
            return []

        edge_stmt = (
            select(GraphEdge.from_id, GraphEdge.to_id)
            .where(
                or_(
                    col(GraphEdge.type) == EdgeType.ASSIGNED_TO,
                    col(GraphEdge.type) == EdgeType.MADE_DECISION,
                )
            )
            .where(or_(col(GraphEdge.from_id).in_(person_ids), col(GraphEdge.to_id).in_(person_ids)))
        )
        connected: set[UUID] = set()
        for from_id, to_id in (await self.session.exec(edge_stmt)).all():
            if from_id not in person_ids:
                connected.add(from_id)
            if to_id not in person_ids:
                connected.add(to_id)
        return list(connected)

    async def _load_source_utterances(self, grounded_node_ids: list[UUID]) -> list[UtteranceHit]:
        if not grounded_node_ids:
            return []

        edge_stmt = (
            select(GraphNode.fields)
            .join(GraphEdge, col(GraphEdge.to_id) == col(GraphNode.id))
            .where(col(GraphEdge.type) == EdgeType.SOURCE)
            .where(col(GraphEdge.from_id).in_(grounded_node_ids))
            .where(col(GraphNode.type) == NodeType.UTTERANCE)
        )
        rows = (await self.session.exec(edge_stmt)).all()
        utterance_ids: set[UUID] = set()
        for fields in rows:
            raw = (fields or {}).get("utterance_id")
            if not raw:
                continue
            try:
                utterance_ids.add(UUID(str(raw)))
            except ValueError:
                continue

        if not utterance_ids:
            return []

        utt_stmt = (
            select(Utterance, Meeting.title, Meeting.started_at, Participant.name)
            .join(Meeting, col(Meeting.id) == col(Utterance.meeting_id))
            .join(Participant, col(Participant.id) == col(Utterance.participant_id), isouter=True)
            .where(col(Utterance.id).in_(utterance_ids))
            .where(col(Utterance.text) != "")
        )
        utt_rows = (await self.session.exec(utt_stmt)).all()
        hits: list[UtteranceHit] = []
        for utt, m_title, m_started, speaker in utt_rows:
            hits.append(
                UtteranceHit(
                    ref="",
                    utterance_id=utt.id,
                    meeting_id=utt.meeting_id,
                    meeting_title=m_title,
                    meeting_started_at=m_started,
                    speaker=speaker,
                    t_start=utt.t_start,
                    t_end=utt.t_end,
                    text=utt.text,
                    score=1.0,
                )
            )
        return hits

    @staticmethod
    def _merge_utterances(primary: list[UtteranceHit], extra: list[UtteranceHit]) -> list[UtteranceHit]:
        seen = {hit.utterance_id for hit in primary}
        merged = list(primary)
        for hit in extra:
            if hit.utterance_id in seen:
                continue
            seen.add(hit.utterance_id)
            merged.append(hit)
        for index, hit in enumerate(merged, start=1):
            hit.ref = f"u{index}"
        return merged

    @staticmethod
    def _extract_name_terms(query: str) -> list[str]:
        terms: list[str] = []
        for word in re.findall(r"[A-Z][a-z]{2,}", query):
            if word not in terms:
                terms.append(word)
        return terms

    async def _build_graph_hits(self, rows: list[tuple[GraphNode, str | None, object]]) -> list[GraphHit]:
        if not rows:
            return []

        node_ids = [node.id for node, _, _ in rows]
        owner_by_node = await self._resolve_owners(node_ids)

        hits: list[GraphHit] = []
        for index, (node, m_title, m_started) in enumerate(rows, start=1):
            text = self._format_node_text(node, owner_by_node.get(node.id))
            if not text:
                continue
            hits.append(
                GraphHit(
                    ref=f"g{index}",
                    node_id=node.id,
                    meeting_id=node.meeting_id,
                    meeting_title=m_title,
                    meeting_started_at=m_started,  # type: ignore[arg-type]
                    type=str(node.type),
                    text=text,
                    score=1.0,
                )
            )
        return hits

    async def _resolve_owners(self, node_ids: list[UUID]) -> dict[UUID, str]:
        if not node_ids:
            return {}

        action_assigned = (
            select(GraphEdge.from_id, GraphNode.fields)
            .join(GraphNode, col(GraphNode.id) == col(GraphEdge.to_id))
            .where(col(GraphEdge.type) == EdgeType.ASSIGNED_TO)
            .where(col(GraphEdge.from_id).in_(node_ids))
            .where(col(GraphNode.type) == NodeType.PERSON)
        )
        decision_made = (
            select(GraphEdge.to_id, GraphNode.fields)
            .join(GraphNode, col(GraphNode.id) == col(GraphEdge.from_id))
            .where(col(GraphEdge.type) == EdgeType.MADE_DECISION)
            .where(col(GraphEdge.to_id).in_(node_ids))
            .where(col(GraphNode.type) == NodeType.PERSON)
        )

        out: dict[UUID, str] = {}
        for node_id, person_fields in (await self.session.exec(action_assigned)).all():
            name = self._person_name(person_fields)
            if name:
                out[node_id] = name
        for node_id, person_fields in (await self.session.exec(decision_made)).all():
            name = self._person_name(person_fields)
            if name and node_id not in out:
                out[node_id] = name
        return out

    @staticmethod
    def _person_name(fields: dict | None) -> str:
        if not fields:
            return ""
        for key in ("name", "title", "text"):
            value = fields.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    @classmethod
    def _format_node_text(cls, node: GraphNode, owner: str | None) -> str:
        body = cls._node_text(node.fields or {})
        if not body:
            return ""
        fields = node.fields or {}
        parts = [body]
        if node.type == NodeType.ACTION_ITEM:
            if owner:
                parts.append(f"owner={owner}")
            due = fields.get("due_date")
            if isinstance(due, str) and due.strip():
                parts.append(f"due={due.strip()}")
            parts.append(f"status={node.status}")
        elif node.type == NodeType.DECISION:
            if owner:
                parts.append(f"by={owner}")
            parts.append(f"status={node.status}")
        elif node.type == NodeType.OPEN_QUESTION:
            parts.append("state=resolved" if node.status == NodeStatus.SUPERSEDED else "state=open")
        return " · ".join(parts)

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

    @staticmethod
    def _node_text(fields: dict) -> str:
        for key in ("text", "title", "summary", "name"):
            value = fields.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return ""
