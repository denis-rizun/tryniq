from datetime import UTC, datetime
from uuid import NAMESPACE_OID, UUID, uuid5

import structlog
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import config
from app.graph.clients.embeddings import get_embedding_client
from app.graph.constants import GROUNDED_NODE_TYPES, EdgeType, NodeStatus, NodeType
from app.graph.exceptions import InvalidGraphOperationError, UngroundedExtractionError, UnknownUtteranceRefError
from app.graph.models import GraphEdge, GraphNode
from app.graph.schemas import (
    AddEdgeOperation,
    AddNodeOperation,
    GraphEdgeRead,
    GraphNodeRead,
    GraphOperation,
    GraphPatchEvent,
    GraphResponse,
    UpdateNodeOperation,
)
from app.transcript.models import Utterance

logger = structlog.get_logger()


class GraphService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_graph(self, meeting_id: UUID) -> GraphResponse:
        nodes = (await self.session.exec(select(GraphNode).where(GraphNode.meeting_id == meeting_id))).all()
        edges = (await self.session.exec(select(GraphEdge).where(GraphEdge.meeting_id == meeting_id))).all()
        return GraphResponse(
            nodes=[GraphNodeRead.model_validate(n) for n in nodes],
            edges=[GraphEdgeRead.model_validate(e) for e in edges],
        )

    async def apply_operations(
        self,
        meeting_id: UUID,
        operations: list[GraphOperation],
        window_utterances: list[Utterance],
        short_refs: dict[str, UUID] | None = None,
    ) -> GraphPatchEvent:
        utterance_lookup = {u.id: u for u in window_utterances}
        short_refs = short_refs or {}
        await self.ensure_meeting_node(meeting_id)

        node_operations = [o for o in operations if isinstance(o, AddNodeOperation)]
        edge_operations = [o for o in operations if isinstance(o, AddEdgeOperation)]
        update_operations = [o for o in operations if isinstance(o, UpdateNodeOperation)]

        self._validate_grounding(node_operations, edge_operations)

        embeddings = await self._batch_embeddings(node_operations)

        temp_to_id: dict[str, UUID] = {}
        added_nodes: list[GraphNode] = []
        for operation, embedding in zip(node_operations, embeddings, strict=True):
            node = await self._add_node(meeting_id, operation, embedding)
            temp_to_id[operation.temp_id] = node.id
            added_nodes.append(node)

        added_edges, grounded_with_source = await self._add_edges(
            meeting_id, edge_operations, temp_to_id, utterance_lookup, short_refs
        )
        for operation in node_operations:
            if operation.node_type in GROUNDED_NODE_TYPES and operation.temp_id not in grounded_with_source:
                raise UngroundedExtractionError()

        updated_nodes: list[GraphNode] = []
        for operation in update_operations:
            node = await self._update_node(meeting_id, operation, temp_to_id)
            updated_nodes.append(node)

        await self.session.commit()
        for n in added_nodes + updated_nodes:
            await self.session.refresh(n)
        for e in added_edges:
            await self.session.refresh(e)

        return GraphPatchEvent(
            meeting_id=meeting_id,
            added_nodes=[GraphNodeRead.model_validate(n) for n in added_nodes],
            added_edges=[GraphEdgeRead.model_validate(e) for e in added_edges],
            updated_nodes=[GraphNodeRead.model_validate(n) for n in updated_nodes],
            timestamp=datetime.now(UTC),
        )

    async def ensure_utterance_node(self, meeting_id: UUID, utterance: Utterance) -> GraphNode:
        node_id = self._utterance_node_id(utterance.id)
        existing = (await self.session.exec(select(GraphNode).where(GraphNode.id == node_id))).one_or_none()
        if existing:
            return existing

        fields = {
            "utterance_id": str(utterance.id),
            "text": utterance.text,
            "t_start": utterance.t_start,
            "t_end": utterance.t_end,
            "participant_id": str(utterance.participant_id),
        }
        stmt = (
            pg_insert(GraphNode)
            .values(
                id=node_id,
                meeting_id=meeting_id,
                type=NodeType.UTTERANCE,
                fields=fields,
                status=NodeStatus.CONFIRMED,
            )
            .on_conflict_do_nothing(index_elements=["id"])
        )
        await self.session.exec(stmt)
        node = (await self.session.exec(select(GraphNode).where(GraphNode.id == node_id))).one()
        return node

    @staticmethod
    def _utterance_node_id(utterance_id: UUID) -> UUID:
        return uuid5(NAMESPACE_OID, f"utterance:{utterance_id}")

    @staticmethod
    def _meeting_node_id(meeting_id: UUID) -> UUID:
        return uuid5(NAMESPACE_OID, f"meeting:{meeting_id}")

    async def ensure_meeting_node(self, meeting_id: UUID) -> GraphNode:
        node_id = self._meeting_node_id(meeting_id)
        existing = (await self.session.exec(select(GraphNode).where(GraphNode.id == node_id))).one_or_none()
        if existing:
            return existing

        stmt = (
            pg_insert(GraphNode)
            .values(
                id=node_id,
                meeting_id=meeting_id,
                type=NodeType.MEETING,
                fields={"meeting_id": str(meeting_id)},
                status=NodeStatus.CONFIRMED,
            )
            .on_conflict_do_nothing(index_elements=["id"])
        )
        await self.session.exec(stmt)
        await self.session.commit()
        node = (await self.session.exec(select(GraphNode).where(GraphNode.id == node_id))).one()
        return node

    @staticmethod
    def _validate_grounding(node_operations: list[AddNodeOperation], edge_operations: list[AddEdgeOperation]) -> None:
        grounded_temp_ids: set[str] = set()
        for edge in edge_operations:
            if edge.edge_type != EdgeType.SOURCE:
                continue

            grounded_temp_ids.add(edge.from_ref)
            grounded_temp_ids.add(edge.to_ref)
        for operation in node_operations:
            if operation.node_type in GROUNDED_NODE_TYPES and operation.temp_id not in grounded_temp_ids:
                raise UngroundedExtractionError()

    async def _add_edges(
        self,
        meeting_id: UUID,
        edge_operations: list[AddEdgeOperation],
        temp_to_id: dict[str, UUID],
        utterance_lookup: dict[UUID, Utterance],
        short_refs: dict[str, UUID],
    ) -> tuple[list[GraphEdge], set[str]]:
        added: list[GraphEdge] = []
        grounded_with_source: set[str] = set()
        for operation in edge_operations:
            edge = await self._add_edge_safely(meeting_id, operation, temp_to_id, utterance_lookup, short_refs)
            if edge is None:
                continue

            added.append(edge)
            if operation.edge_type == EdgeType.SOURCE and operation.from_ref in temp_to_id:
                grounded_with_source.add(operation.from_ref)
            if operation.edge_type == EdgeType.SOURCE and operation.to_ref in temp_to_id:
                grounded_with_source.add(operation.to_ref)
        return added, grounded_with_source

    async def _batch_embeddings(self, node_operations: list[AddNodeOperation]) -> list[list[float] | None]:
        texts = [self._node_text(operation.fields) for operation in node_operations]
        non_empty_indices = [i for i, t in enumerate(texts) if t]
        if not non_empty_indices:
            return [None] * len(node_operations)

        vectors = await get_embedding_client().embed_many([texts[i] for i in non_empty_indices])
        result: list[list[float] | None] = [None] * len(node_operations)
        for i, vec in zip(non_empty_indices, vectors, strict=True):
            result[i] = vec
        return result

    async def _add_node(
        self,
        meeting_id: UUID,
        operation: AddNodeOperation,
        embedding: list[float] | None,
    ) -> GraphNode:
        if embedding is not None:
            existing = await self._dedup_node(meeting_id, operation.node_type, embedding)
            if existing is not None:
                return existing

        node = GraphNode(
            meeting_id=meeting_id,
            type=operation.node_type,
            fields=operation.fields,
            status=operation.status,
            embedding=embedding,
        )
        self.session.add(node)
        await self.session.flush()
        return node

    async def _add_edge_safely(
        self,
        meeting_id: UUID,
        operation: AddEdgeOperation,
        temp_to_id: dict[str, UUID],
        utterance_lookup: dict[UUID, Utterance],
        short_refs: dict[str, UUID],
    ) -> GraphEdge | None:
        try:
            from_id = await self._resolve_ref(
                meeting_id, operation.from_ref, temp_to_id, utterance_lookup, short_refs
            )
            to_id = await self._resolve_ref(
                meeting_id, operation.to_ref, temp_to_id, utterance_lookup, short_refs
            )
        except (UnknownUtteranceRefError, InvalidGraphOperationError) as e:
            logger.warning(
                "Dropping edge with unresolved ref",
                edge_type=operation.edge_type,
                from_ref=operation.from_ref,
                to_ref=operation.to_ref,
                reason=str(e),
            )
            return None

        edge = GraphEdge(meeting_id=meeting_id, type=operation.edge_type, from_id=from_id, to_id=to_id)
        self.session.add(edge)
        await self.session.flush()
        return edge

    async def _update_node(
        self, meeting_id: UUID, operation: UpdateNodeOperation, temp_to_id: dict[str, UUID]
    ) -> GraphNode:
        node_id = temp_to_id.get(operation.id)
        if node_id is None:
            try:
                node_id = UUID(operation.id)
            except ValueError as e:
                raise InvalidGraphOperationError() from e

        node = (
            await self.session.exec(
                select(GraphNode).where(GraphNode.id == node_id).where(GraphNode.meeting_id == meeting_id)
            )
        ).one_or_none()
        if not node:
            raise InvalidGraphOperationError()

        if operation.fields is not None:
            merged = dict(node.fields)
            merged.update(operation.fields)
            node.fields = merged
        if operation.status is not None:
            node.status = operation.status

        self.session.add(node)
        await self.session.flush()
        return node

    async def _resolve_ref(
        self,
        meeting_id: UUID,
        ref: str,
        temp_to_id: dict[str, UUID],
        utterance_lookup: dict[UUID, Utterance],
        short_refs: dict[str, UUID],
    ) -> UUID:
        if ref in temp_to_id:
            return temp_to_id[ref]

        if ref in short_refs:
            uid = short_refs[ref]
            if uid == meeting_id:
                return self._meeting_node_id(meeting_id)
            if uid in utterance_lookup:
                node = await self.ensure_utterance_node(meeting_id, utterance_lookup[uid])
                return node.id

        try:
            uid = UUID(ref)
        except ValueError as e:
            raise InvalidGraphOperationError() from e

        if uid == meeting_id:
            return self._meeting_node_id(meeting_id)

        if uid in utterance_lookup:
            node = await self.ensure_utterance_node(meeting_id, utterance_lookup[uid])
            return node.id

        existing = (
            await self.session.exec(
                select(GraphNode).where(GraphNode.id == uid).where(GraphNode.meeting_id == meeting_id)
            )
        ).one_or_none()
        if existing is None:
            raise UnknownUtteranceRefError()

        return existing.id

    async def _dedup_node(
        self,
        meeting_id: UUID,
        node_type: NodeType,
        embedding: list[float],
    ) -> GraphNode | None:
        threshold = config.graph.DEDUP_COSINE_THRESHOLD
        query = (
            select(GraphNode)
            .where(GraphNode.meeting_id == meeting_id)
            .where(GraphNode.type == node_type)
            .where(col(GraphNode.embedding).is_not(None))
            .order_by(col(GraphNode.embedding).cosine_distance(embedding))
            .limit(1)
        )
        candidate = (await self.session.exec(query)).one_or_none()
        if candidate is None or candidate.embedding is None:
            return None

        similarity = 1.0 - _cosine_distance(candidate.embedding, embedding)
        if similarity >= threshold:
            return candidate
        return None

    @staticmethod
    def _node_text(fields: dict) -> str:
        for key in ("text", "title", "summary", "name"):
            value = fields.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return ""


def _cosine_distance(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 1.0
    return 1.0 - (dot / (na * nb))
