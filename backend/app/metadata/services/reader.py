from uuid import UUID

from sqlalchemy import bindparam, text
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.graph.constants import EdgeType, NodeType
from app.graph.models import GraphEdge, GraphNode
from app.graph.services.graph import GraphService
from app.meeting.models import Meeting
from app.metadata.schemas import (
    ActionItemProjection,
    DecisionProjection,
    MeetingMetadataResponse,
    OpenQuestionProjection,
    RelatedMeetingProjection,
    TopicProjection,
)
from app.metadata.services.graph_index import GraphIndex


class MetadataReader:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def read(self, meeting_id: UUID) -> MeetingMetadataResponse:
        meeting = (await self.session.exec(select(Meeting).where(Meeting.id == meeting_id))).one()
        nodes = list((await self.session.exec(select(GraphNode).where(GraphNode.meeting_id == meeting_id))).all())
        edges = list((await self.session.exec(select(GraphEdge).where(GraphEdge.meeting_id == meeting_id))).all())

        index = GraphIndex(nodes, edges)
        decisions = [self._decision(n, index) for n in nodes if n.type == NodeType.DECISION]
        actions = [self._action_item(n, index) for n in nodes if n.type == NodeType.ACTION_ITEM]
        questions = [self._open_question(n, index) for n in nodes if n.type == NodeType.OPEN_QUESTION]
        topics = [self._topic(n) for n in nodes if n.type == NodeType.TOPIC]
        related = await self._related(meeting_id, index)

        return MeetingMetadataResponse(
            meeting_id=meeting.id,
            summary=meeting.summary,
            metadata_generated_at=meeting.metadata_generated_at,
            decisions=decisions,
            action_items=actions,
            open_questions=questions,
            topics=topics,
            related_meetings=related,
        )

    @staticmethod
    def _decision(node: GraphNode, index: GraphIndex) -> DecisionProjection:
        utt_id, t_start = index.source(node.id)
        return DecisionProjection(
            id=node.id,
            text=str((node.fields or {}).get("text", "")),
            status=node.status,
            owner_name=index.owner(node.id, EdgeType.MADE_DECISION, "in"),
            source_t_start=t_start,
            source_utterance_id=utt_id,
            topic_ids=index.topic_ids(node.id),
        )

    @staticmethod
    def _action_item(node: GraphNode, index: GraphIndex) -> ActionItemProjection:
        utt_id, t_start = index.source(node.id)
        fields = node.fields or {}
        return ActionItemProjection(
            id=node.id,
            text=str(fields.get("text", "")),
            status=node.status,
            due_date=fields.get("due_date"),
            owner_name=index.owner(node.id, EdgeType.ASSIGNED_TO, "out"),
            source_t_start=t_start,
            source_utterance_id=utt_id,
            topic_ids=index.topic_ids(node.id),
        )

    @staticmethod
    def _open_question(node: GraphNode, index: GraphIndex) -> OpenQuestionProjection:
        utt_id, t_start = index.source(node.id)
        return OpenQuestionProjection(
            id=node.id,
            text=str((node.fields or {}).get("text", "")),
            status=node.status,
            source_t_start=t_start,
            source_utterance_id=utt_id,
            topic_ids=index.topic_ids(node.id),
        )

    @staticmethod
    def _topic(node: GraphNode) -> TopicProjection:
        fields = node.fields or {}
        return TopicProjection(
            id=node.id,
            name=str(fields.get("title") or fields.get("name") or ""),
            summary=fields.get("summary"),
            relates_previous=False,
        )

    async def _related(self, meeting_id: UUID, index: GraphIndex) -> list[RelatedMeetingProjection]:
        meeting_node_id = GraphService.get_meeting_node_id(meeting_id)
        related_ids = index.related_meeting_ids(meeting_node_id)
        if not related_ids:
            return []

        rows = (await self.session.exec(select(Meeting).where(col(Meeting.id).in_(related_ids)))).all()
        meetings_by_id = {m.id: m for m in rows}
        shared_topics = await self._shared_topic_names(meeting_id, related_ids)

        result: list[RelatedMeetingProjection] = []
        for mid in related_ids:
            meeting = meetings_by_id.get(mid)
            if not meeting:
                continue

            result.append(
                RelatedMeetingProjection(
                    id=meeting.id,
                    title=meeting.title,
                    started_at=meeting.started_at,
                    shared_topic_names=shared_topics.get(mid, []),
                )
            )
        return result

    async def _shared_topic_names(self, meeting_id: UUID, other_ids: list[UUID]) -> dict[UUID, list[str]]:
        query = text(
            """
            SELECT other.meeting_id AS other_meeting_id, (other.fields->>'title') AS title
            FROM graph_node this
            JOIN graph_node other
              ON other.type = this.type
              AND other.meeting_id <> this.meeting_id
              AND (this.embedding <=> other.embedding) <= 0.15
            WHERE this.meeting_id = :meeting_id AND this.type = 'TOPIC'
              AND other.meeting_id = ANY(:other_ids)
            """
        ).bindparams(
            bindparam("meeting_id", value=str(meeting_id)),
            bindparam("other_ids", value=[str(i) for i in other_ids]),
        )
        rows = (await self.session.exec(query)).all()

        result: dict[UUID, list[str]] = {}
        for raw_id, title in rows:
            if not isinstance(title, str) or not title.strip():
                continue

            other_id = raw_id if isinstance(raw_id, UUID) else UUID(str(raw_id))
            titles = result.setdefault(other_id, [])
            if title not in titles:
                titles.append(title)
        return result
