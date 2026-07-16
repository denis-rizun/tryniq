import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlmodel import col, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.chat.constants import CHAT_RETRIEVAL_GRAPH_TYPES
from app.graph.constants import EdgeType, NodeStatus, NodeType
from app.graph.models import GraphEdge, GraphNode
from app.meeting.constants import MeetingStatus
from app.meeting.models import Meeting


@dataclass(slots=True)
class GraphHit:
    ref: str
    node_id: UUID
    meeting_id: UUID
    meeting_title: str | None
    meeting_started_at: datetime | None
    type: str
    text: str
    score: float


class GraphHitBuilder:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load_meeting_graph(self, meeting_id: UUID) -> list[GraphHit]:
        types = [NodeType(value) for value in CHAT_RETRIEVAL_GRAPH_TYPES]
        statement = (
            select(GraphNode, Meeting.title, Meeting.started_at)
            .join(Meeting, col(Meeting.id) == col(GraphNode.meeting_id))
            .where(col(GraphNode.meeting_id) == meeting_id)
            .where(col(GraphNode.type).in_(types))
        )
        rows = (await self._session.exec(statement)).all()
        return await self._build([(node, title, started_at) for node, title, started_at in rows])

    async def search_all(self, query: str, query_vector: list[float], top_k: int) -> list[GraphHit]:
        types = [NodeType(value) for value in CHAT_RETRIEVAL_GRAPH_TYPES]
        distance = col(GraphNode.embedding).cosine_distance(query_vector)
        statement = (
            select(GraphNode, Meeting.title, Meeting.started_at)
            .join(Meeting, col(Meeting.id) == col(GraphNode.meeting_id))
            .where(col(GraphNode.type).in_(types))
            .where(col(GraphNode.embedding).is_not(None))
            .where(col(Meeting.status) == MeetingStatus.FINAL)
            .order_by(distance)
            .limit(top_k)
        )
        rows = list((await self._session.exec(statement)).all())

        boosted_ids = await self._person_boost_node_ids(query)
        if boosted_ids:
            existing_ids = {node.id for node, _, _ in rows}
            extra_ids = [node_id for node_id in boosted_ids if node_id not in existing_ids]
            if extra_ids:
                extra_statement = (
                    select(GraphNode, Meeting.title, Meeting.started_at)
                    .join(Meeting, col(Meeting.id) == col(GraphNode.meeting_id))
                    .where(col(GraphNode.id).in_(extra_ids))
                    .where(col(Meeting.status) == MeetingStatus.FINAL)
                )
                rows.extend((await self._session.exec(extra_statement)).all())

        return await self._build([(node, title, started_at) for node, title, started_at in rows])

    async def _person_boost_node_ids(self, query: str) -> list[UUID]:
        terms = self._extract_name_terms(query)
        if not terms:
            return []

        like_clauses = [col(GraphNode.fields).op("->>")("name").ilike(f"%{term}%") for term in terms]
        person_statement = select(GraphNode.id).where(col(GraphNode.type) == NodeType.PERSON).where(or_(*like_clauses))
        person_ids = list((await self._session.exec(person_statement)).all())
        if not person_ids:
            return []

        edge_statement = (
            select(GraphEdge.from_id, GraphEdge.to_id)
            .where(or_(col(GraphEdge.type) == EdgeType.ASSIGNED_TO, col(GraphEdge.type) == EdgeType.MADE_DECISION))
            .where(or_(col(GraphEdge.from_id).in_(person_ids), col(GraphEdge.to_id).in_(person_ids)))
        )
        connected_ids: set[UUID] = set()
        for from_id, to_id in (await self._session.exec(edge_statement)).all():
            if from_id not in person_ids:
                connected_ids.add(from_id)

            if to_id not in person_ids:
                connected_ids.add(to_id)

        return list(connected_ids)

    async def _build(self, rows: list[tuple[GraphNode, str | None, datetime | None]]) -> list[GraphHit]:
        if not rows:
            return []

        owner_by_node = await self._resolve_owners([node.id for node, _, _ in rows])
        hits: list[GraphHit] = []
        for index, (node, title, started_at) in enumerate(rows, start=1):
            text = self._format_node_text(node, owner_by_node.get(node.id))
            if text:
                hits.append(
                    GraphHit(
                        ref=f"g{index}",
                        node_id=node.id,
                        meeting_id=node.meeting_id,
                        meeting_title=title,
                        meeting_started_at=started_at,
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

        owners: dict[UUID, str] = {}
        for node_id, fields in (await self._session.exec(action_assigned)).all():
            if name := self._person_name(fields):
                owners[node_id] = name

        for node_id, fields in (await self._session.exec(decision_made)).all():
            if name := self._person_name(fields):
                owners.setdefault(node_id, name)

        return owners

    @staticmethod
    def _extract_name_terms(query: str) -> list[str]:
        terms: list[str] = []
        for word in re.findall(r"[A-Z][a-z]{2,}", query):
            if word not in terms:
                terms.append(word)

        return terms

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
        fields = node.fields or {}
        body = cls._node_text(fields)
        if not body:
            return ""

        parts = [body]
        if node.type == NodeType.ACTION_ITEM:
            if owner:
                parts.append(f"owner={owner}")
            due_date = fields.get("due_date")
            if isinstance(due_date, str) and due_date.strip():
                parts.append(f"due={due_date.strip()}")
            parts.append(f"status={node.status}")
        elif node.type == NodeType.DECISION:
            if owner:
                parts.append(f"by={owner}")
            parts.append(f"status={node.status}")
        elif node.type == NodeType.OPEN_QUESTION:
            parts.append("state=resolved" if node.status == NodeStatus.SUPERSEDED else "state=open")
        return " · ".join(parts)

    @staticmethod
    def _node_text(fields: dict) -> str:
        for key in ("text", "title", "summary", "name"):
            value = fields.get(key)
            if isinstance(value, str) and value.strip():
                return value

        return ""
