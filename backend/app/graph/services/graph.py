from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.graph.models import GraphEdge, GraphNode
from app.graph.schemas import GraphEdgeResponse, GraphNodeResponse, GraphOperation, GraphPatchEvent, GraphResponse
from app.graph.services.dedup import GraphNodeDeduplicator
from app.graph.services.operations import GraphOperationApplier
from app.graph.services.registry import GraphNodeRegistry
from app.participant.models import Participant
from app.transcript.models import Utterance


class GraphService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.registry = GraphNodeRegistry(session)
        self.applier = GraphOperationApplier(session, self.registry, GraphNodeDeduplicator(session))

    async def get_graph(self, meeting_id: UUID) -> GraphResponse:
        nodes = (await self.session.exec(select(GraphNode).where(GraphNode.meeting_id == meeting_id))).all()
        edges = (await self.session.exec(select(GraphEdge).where(GraphEdge.meeting_id == meeting_id))).all()
        return GraphResponse(
            nodes=[GraphNodeResponse.model_validate(node) for node in nodes],
            edges=[GraphEdgeResponse.model_validate(edge) for edge in edges],
        )

    async def apply_operations(
        self,
        meeting_id: UUID,
        operations: list[GraphOperation],
        window_utterances: list[Utterance],
        short_refs: dict[str, UUID] | None = None,
    ) -> GraphPatchEvent:
        nodes, edges, updates = await self.applier.apply_operations(
            meeting_id, operations, window_utterances, short_refs
        )
        await self.session.commit()
        for node in nodes + updates:
            await self.session.refresh(node)
        for edge in edges:
            await self.session.refresh(edge)
        return GraphPatchEvent(
            meeting_id=meeting_id,
            added_nodes=[GraphNodeResponse.model_validate(node) for node in nodes],
            added_edges=[GraphEdgeResponse.model_validate(edge) for edge in edges],
            updated_nodes=[GraphNodeResponse.model_validate(node) for node in updates],
            timestamp=datetime.now(UTC),
        )

    async def ensure_utterance_node(self, meeting_id: UUID, utterance: Utterance) -> GraphNode:
        return await self.registry.ensure_utterance_node(meeting_id, utterance)

    async def ensure_person_node(self, meeting_id: UUID, participant: Participant) -> GraphNode:
        return await self.registry.ensure_person_node(meeting_id, participant)

    async def ensure_meeting_node(self, meeting_id: UUID) -> GraphNode:
        return await self.registry.ensure_meeting_node(meeting_id)

    @staticmethod
    def get_meeting_node_id(meeting_id: UUID) -> UUID:
        return GraphNodeRegistry.get_meeting_node_id(meeting_id)
