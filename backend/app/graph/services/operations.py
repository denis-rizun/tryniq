from uuid import UUID

import structlog
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.graph.constants import GROUNDED_NODE_TYPES, EdgeType
from app.graph.exceptions import InvalidGraphOperationError, UngroundedExtractionError, UnknownUtteranceRefError
from app.graph.models import GraphEdge, GraphNode
from app.graph.schemas import AddEdgeOperation, AddNodeOperation, GraphOperation, UpdateNodeOperation
from app.graph.services.dedup import GraphNodeDeduplicator
from app.graph.services.registry import GraphNodeRegistry
from app.transcript.models import Utterance

logger = structlog.get_logger()


class GraphOperationApplier:
    def __init__(self, session: AsyncSession, registry: GraphNodeRegistry, deduplicator: GraphNodeDeduplicator) -> None:
        self.session = session
        self.registry = registry
        self.deduplicator = deduplicator

    async def apply_operations(
        self,
        meeting_id: UUID,
        operations: list[GraphOperation],
        window_utterances: list[Utterance],
        short_refs: dict[str, UUID] | None = None,
    ) -> tuple[list[GraphNode], list[GraphEdge], list[GraphNode]]:
        await self.registry.ensure_meeting_node(meeting_id)
        refs = short_refs or {}
        utterances = {utterance.id: utterance for utterance in window_utterances}
        node_operations = [operation for operation in operations if isinstance(operation, AddNodeOperation)]
        edge_operations = [operation for operation in operations if isinstance(operation, AddEdgeOperation)]
        update_operations = [operation for operation in operations if isinstance(operation, UpdateNodeOperation)]
        self._validate_grounding(node_operations, edge_operations)

        node_ids: dict[str, UUID] = {}
        added_nodes: list[GraphNode] = []
        embeddings = await self.deduplicator.batch_embeddings(node_operations)
        for operation, embedding in zip(node_operations, embeddings, strict=True):
            node = await self._add_node(meeting_id, operation, embedding)
            node_ids[operation.temp_id] = node.id
            added_nodes.append(node)
        added_edges, grounded = await self._add_edges(meeting_id, edge_operations, node_ids, utterances, refs)
        if any(
            operation.node_type in GROUNDED_NODE_TYPES and operation.temp_id not in grounded
            for operation in node_operations
        ):
            raise UngroundedExtractionError()

        updated_nodes = [await self._update_node(meeting_id, operation, node_ids) for operation in update_operations]
        return added_nodes, added_edges, updated_nodes

    @staticmethod
    def _validate_grounding(nodes: list[AddNodeOperation], edges: list[AddEdgeOperation]) -> None:
        grounded = {
            reference
            for edge in edges
            if edge.edge_type == EdgeType.SOURCE
            for reference in (edge.from_ref, edge.to_ref)
        }
        if any(node.node_type in GROUNDED_NODE_TYPES and node.temp_id not in grounded for node in nodes):
            raise UngroundedExtractionError()

    async def _add_node(
        self, meeting_id: UUID, operation: AddNodeOperation, embedding: list[float] | None
    ) -> GraphNode:
        if embedding is not None:
            existing = await self.deduplicator.dedup_node(meeting_id, operation.node_type, embedding)
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

    async def _add_edges(
        self,
        meeting_id: UUID,
        operations: list[AddEdgeOperation],
        node_ids: dict[str, UUID],
        utterances: dict[UUID, Utterance],
        refs: dict[str, UUID],
    ) -> tuple[list[GraphEdge], set[str]]:
        edges: list[GraphEdge] = []
        grounded: set[str] = set()
        for operation in operations:
            try:
                from_id = await self._resolve_ref(meeting_id, operation.from_ref, node_ids, utterances, refs)
                to_id = await self._resolve_ref(meeting_id, operation.to_ref, node_ids, utterances, refs)
            except (UnknownUtteranceRefError, InvalidGraphOperationError) as exc:
                logger.warning("Dropping edge with unresolved ref", edge_type=operation.edge_type, reason=str(exc))
                continue

            edge = GraphEdge(meeting_id=meeting_id, type=operation.edge_type, from_id=from_id, to_id=to_id)
            self.session.add(edge)
            await self.session.flush()
            edges.append(edge)
            if operation.edge_type == EdgeType.SOURCE:
                grounded.update(
                    reference for reference in (operation.from_ref, operation.to_ref) if reference in node_ids
                )
        return edges, grounded

    async def _update_node(
        self, meeting_id: UUID, operation: UpdateNodeOperation, node_ids: dict[str, UUID]
    ) -> GraphNode:
        node_id = node_ids.get(operation.id)
        if node_id is None:
            try:
                node_id = UUID(operation.id)
            except ValueError as exc:
                raise InvalidGraphOperationError() from exc

        node = (
            await self.session.exec(
                select(GraphNode).where(GraphNode.id == node_id).where(GraphNode.meeting_id == meeting_id)
            )
        ).one_or_none()
        if node is None:
            raise InvalidGraphOperationError()

        if operation.fields is not None:
            node.fields = {**node.fields, **operation.fields}
        if operation.status is not None:
            node.status = operation.status
        self.session.add(node)
        await self.session.flush()
        return node

    async def _resolve_ref(
        self,
        meeting_id: UUID,
        ref: str,
        node_ids: dict[str, UUID],
        utterances: dict[UUID, Utterance],
        refs: dict[str, UUID],
    ) -> UUID:
        if ref in node_ids:
            return node_ids[ref]

        raw_id = refs.get(ref)
        if raw_id is None:
            try:
                raw_id = UUID(ref)
            except ValueError as exc:
                raise InvalidGraphOperationError() from exc

        if raw_id == meeting_id:
            return self.registry.get_meeting_node_id(meeting_id)

        if raw_id in utterances:
            return (await self.registry.ensure_utterance_node(meeting_id, utterances[raw_id])).id

        existing = (
            await self.session.exec(
                select(GraphNode).where(GraphNode.id == raw_id).where(GraphNode.meeting_id == meeting_id)
            )
        ).one_or_none()
        if existing is None:
            raise UnknownUtteranceRefError()

        return existing.id
