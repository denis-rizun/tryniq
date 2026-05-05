from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import col, delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.client import AIClient
from app.graph.constants import EdgeType, NodeStatus, NodeType
from app.graph.models import GraphEdge, GraphNode
from app.graph.service import GraphService
from app.meeting.models import Meeting
from app.metadata.constants import GENERATED_NODE_TYPES
from app.metadata.schemas import (
    ExtractedActionItem,
    ExtractedDecision,
    ExtractedMetadata,
    ExtractedOpenQuestion,
    ExtractedTopic,
)
from app.metadata.services.references import MetadataReferences
from app.participant.models import Participant


class MetadataGraphWriter:
    def __init__(self, session: AsyncSession, graph_service: GraphService, ai_client: AIClient) -> None:
        self.session = session
        self.graph = graph_service
        self.ai = ai_client

    async def reset_generated(self, meeting_id: UUID) -> None:
        await self.session.exec(
            delete(GraphNode)
            .where(GraphNode.meeting_id == meeting_id)
            .where(col(GraphNode.type).in_(GENERATED_NODE_TYPES))
        )
        await self.session.exec(
            delete(GraphEdge)
            .where(GraphEdge.meeting_id == meeting_id)
            .where(GraphEdge.type == EdgeType.RELATES_TO)
        )
        await self.session.flush()

    async def ensure_persons(self, meeting_id: UUID, participants: list[Participant]) -> dict[str, UUID]:
        await self.graph.ensure_meeting_node(meeting_id)
        result: dict[str, UUID] = {}
        meeting_node_id = GraphService.get_meeting_node_id(meeting_id)
        for p in participants:
            node = await self.graph.ensure_person_node(meeting_id, p)
            result[MetadataReferences.get_person_ref(p.id)] = node.id
            await self._upsert_edge(meeting_id, EdgeType.PARTICIPATED_IN, node.id, meeting_node_id)
        return result

    async def write_metadata(
        self,
        meeting_id: UUID,
        metadata: ExtractedMetadata,
        references: MetadataReferences,
        person_ref_to_node: dict[str, UUID],
    ) -> None:
        topic_ids = await self._write_topics(meeting_id, metadata.topics)
        await self._write_decisions(meeting_id, metadata.decisions, references, topic_ids, person_ref_to_node)
        await self._write_action_items(meeting_id, metadata.action_items, references, topic_ids, person_ref_to_node)
        await self._write_open_questions(meeting_id, metadata.open_questions, references, topic_ids)

        meeting_node_id = GraphService.get_meeting_node_id(meeting_id)
        for topic_id in topic_ids.values():
            await self._upsert_edge(meeting_id, EdgeType.DISCUSSED_IN, topic_id, meeting_node_id)

    async def persist_summary(self, meeting: Meeting, summary: str | None) -> None:
        meeting.summary = summary
        meeting.metadata_generated_at = datetime.now(UTC)
        embeddings = await self._embed([summary]) if summary else [None]
        meeting.summary_embedding = embeddings[0]
        self.session.add(meeting)
        await self.session.flush()

    async def link_related_meetings(self, meeting_id: UUID, ranked_ids: list[UUID]) -> None:
        meeting_node_id = GraphService.get_meeting_node_id(meeting_id)
        for other_id in ranked_ids:
            await self.graph.ensure_meeting_node(other_id)
            other_node_id = GraphService.get_meeting_node_id(other_id)
            await self._upsert_edge(meeting_id, EdgeType.RELATES_TO, meeting_node_id, other_node_id)

    async def _write_topics(self, meeting_id: UUID, topics: list[ExtractedTopic]) -> dict[str, UUID]:
        texts = [t.title + (f". {t.summary}" if t.summary else "") for t in topics]
        embeddings = await self._embed(texts)
        result: dict[str, UUID] = {}
        for topic, emb in zip(topics, embeddings, strict=True):
            node = await self._add_topic_node(meeting_id, topic, emb)
            result[topic.temp_id] = node.id
        return result

    async def _write_decisions(
        self,
        meeting_id: UUID,
        decisions: list[ExtractedDecision],
        references: MetadataReferences,
        topic_ids: dict[str, UUID],
        person_ref_to_node: dict[str, UUID],
    ) -> None:
        embeddings = await self._embed([d.text for d in decisions])
        for decision, emb in zip(decisions, embeddings, strict=True):
            node = await self._save_node(meeting_id, NodeType.DECISION, {"text": decision.text}, decision.status, emb)
            await self._link_sources(meeting_id, node.id, decision.source_utterance_refs, references)
            await self._link_topics(meeting_id, node.id, decision.topic_refs, topic_ids)
            person_id = person_ref_to_node.get(decision.decided_by_person_ref or "")
            if person_id:
                await self._upsert_edge(meeting_id, EdgeType.MADE_DECISION, person_id, node.id)

    async def _write_action_items(
        self,
        meeting_id: UUID,
        actions: list[ExtractedActionItem],
        references: MetadataReferences,
        topic_ids: dict[str, UUID],
        person_ref_to_node: dict[str, UUID],
    ) -> None:
        embeddings = await self._embed([a.text for a in actions])
        for action, emb in zip(actions, embeddings, strict=True):
            fields: dict = {"text": action.text}
            if action.due_date:
                fields["due_date"] = action.due_date
            node = await self._save_node(meeting_id, NodeType.ACTION_ITEM, fields, action.status, emb)
            await self._link_sources(meeting_id, node.id, action.source_utterance_refs, references)
            await self._link_topics(meeting_id, node.id, action.topic_refs, topic_ids)
            person_id = person_ref_to_node.get(action.assignee_person_ref or "")
            if person_id:
                await self._upsert_edge(meeting_id, EdgeType.ASSIGNED_TO, node.id, person_id)

    async def _write_open_questions(
        self,
        meeting_id: UUID,
        questions: list[ExtractedOpenQuestion],
        references: MetadataReferences,
        topic_ids: dict[str, UUID],
    ) -> None:
        embeddings = await self._embed([q.text for q in questions])
        for question, emb in zip(questions, embeddings, strict=True):
            fields = {"text": question.text}
            node = await self._save_node(meeting_id, NodeType.OPEN_QUESTION, fields, question.status, emb)
            await self._link_sources(meeting_id, node.id, question.source_utterance_refs, references)
            await self._link_topics(meeting_id, node.id, question.topic_refs, topic_ids)

    async def _add_topic_node(
        self,
        meeting_id: UUID,
        topic: ExtractedTopic,
        embedding: list[float] | None,
    ) -> GraphNode:
        if embedding:
            existing = await self.graph.dedup_node(meeting_id, NodeType.TOPIC, embedding)
            if existing:
                return existing

        fields: dict = {"title": topic.title}
        if topic.summary:
            fields["summary"] = topic.summary
        return await self._save_node(meeting_id, NodeType.TOPIC, fields, NodeStatus.CONFIRMED, embedding)

    async def _save_node(
        self,
        meeting_id: UUID,
        node_type: NodeType,
        fields: dict,
        status: NodeStatus,
        embedding: list[float] | None,
    ) -> GraphNode:
        node = GraphNode(
            meeting_id=meeting_id, type=node_type, fields=fields, status=status, embedding=embedding
        )
        self.session.add(node)
        await self.session.flush()
        return node

    async def _link_sources(
        self,
        meeting_id: UUID,
        node_id: UUID,
        refs: list[str],
        references: MetadataReferences,
    ) -> None:
        utt_by_id = {u.id: u for u in references.utterances}
        for ref in refs:
            uid = references.utterance_by_token.get(ref)
            utterance = utt_by_id.get(uid) if uid else None
            if not utterance:
                continue

            utt_node = await self.graph.ensure_utterance_node(meeting_id, utterance)
            await self._upsert_edge(meeting_id, EdgeType.SOURCE, node_id, utt_node.id)

    async def _link_topics(
        self,
        meeting_id: UUID,
        node_id: UUID,
        topic_refs: list[str],
        topic_ids: dict[str, UUID],
    ) -> None:
        for ref in topic_refs:
            topic_id = topic_ids.get(ref)
            if not topic_id:
                continue

            await self._upsert_edge(meeting_id, EdgeType.ABOUT_TOPIC, node_id, topic_id)

    async def _upsert_edge(
        self, meeting_id: UUID, edge_type: EdgeType, from_id: UUID, to_id: UUID
    ) -> None:
        existing = (
            await self.session.exec(
                select(GraphEdge)
                .where(GraphEdge.meeting_id == meeting_id)
                .where(GraphEdge.type == edge_type)
                .where(GraphEdge.from_id == from_id)
                .where(GraphEdge.to_id == to_id)
                .limit(1)
            )
        ).one_or_none()
        if existing:
            return

        edge = GraphEdge(meeting_id=meeting_id, type=edge_type, from_id=from_id, to_id=to_id)
        self.session.add(edge)
        await self.session.flush()

    async def _embed(self, texts: list[str]) -> list[list[float] | None]:
        non_empty = [(i, t) for i, t in enumerate(texts) if t.strip()]
        if not non_empty:
            return [None] * len(texts)

        vectors = await self.ai.embed([t for _, t in non_empty])
        result: list[list[float] | None] = [None] * len(texts)
        for (i, _), vec in zip(non_empty, vectors, strict=True):
            result[i] = vec
        return result
