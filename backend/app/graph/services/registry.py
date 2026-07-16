from uuid import NAMESPACE_OID, UUID, uuid5

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.graph.constants import NodeStatus, NodeType
from app.graph.models import GraphNode
from app.participant.models import Participant
from app.transcript.models import Utterance


class GraphNodeRegistry:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ensure_utterance_node(self, meeting_id: UUID, utterance: Utterance) -> GraphNode:
        node_id = self._get_utterance_node_id(utterance.id)
        existing = (await self.session.exec(select(GraphNode).where(GraphNode.id == node_id))).one_or_none()
        if existing:
            return existing

        node = GraphNode(
            id=node_id,
            meeting_id=meeting_id,
            type=NodeType.UTTERANCE,
            fields={
                "utterance_id": str(utterance.id),
                "text": utterance.text,
                "t_start": utterance.t_start,
                "t_end": utterance.t_end,
                "participant_id": str(utterance.participant_id),
            },
            status=NodeStatus.CONFIRMED,
        )
        return await self._insert(node)

    async def ensure_person_node(self, meeting_id: UUID, participant: Participant) -> GraphNode:
        node = GraphNode(
            id=self._get_person_node_id(participant.id),
            meeting_id=meeting_id,
            type=NodeType.PERSON,
            fields={"name": participant.name, "participant_id": str(participant.id)},
            status=NodeStatus.CONFIRMED,
        )
        return await self._insert(node)

    async def ensure_meeting_node(self, meeting_id: UUID) -> GraphNode:
        node = GraphNode(
            id=self.get_meeting_node_id(meeting_id),
            meeting_id=meeting_id,
            type=NodeType.MEETING,
            fields={"meeting_id": str(meeting_id)},
            status=NodeStatus.CONFIRMED,
        )
        result = await self._insert(node, commit=True)
        return result

    async def _insert(self, node: GraphNode, commit: bool = False) -> GraphNode:
        existing = (await self.session.exec(select(GraphNode).where(GraphNode.id == node.id))).one_or_none()
        if existing:
            return existing

        statement = (
            pg_insert(GraphNode)
            .values(
                id=node.id,
                meeting_id=node.meeting_id,
                type=node.type,
                fields=node.fields,
                status=node.status,
            )
            .on_conflict_do_nothing(index_elements=["id"])
        )
        await self.session.exec(statement)
        if commit:
            await self.session.commit()

        return (await self.session.exec(select(GraphNode).where(GraphNode.id == node.id))).one()

    @staticmethod
    def _get_utterance_node_id(utterance_id: UUID) -> UUID:
        return uuid5(NAMESPACE_OID, f"utterance:{utterance_id}")

    @staticmethod
    def get_meeting_node_id(meeting_id: UUID) -> UUID:
        return uuid5(NAMESPACE_OID, f"meeting:{meeting_id}")

    @staticmethod
    def _get_person_node_id(participant_id: UUID) -> UUID:
        return uuid5(NAMESPACE_OID, f"person:{participant_id}")
