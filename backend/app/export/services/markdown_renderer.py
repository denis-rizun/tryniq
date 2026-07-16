from collections import defaultdict
from datetime import datetime
from uuid import UUID

from app.export.constants import SectionId
from app.graph.constants import NodeType
from app.graph.schemas import GraphNodeResponse, GraphResponse
from app.meeting.models import Meeting
from app.metadata.schemas import (
    ActionItemProjection,
    DecisionProjection,
    MeetingMetadataResponse,
    OpenQuestionProjection,
    TopicProjection,
)
from app.participant.schemas import ParticipantResponse
from app.transcript.schemas import TranscriptResponse, UtteranceResponse


class MarkdownRenderer:
    def render(
        self,
        meeting: Meeting,
        transcript: TranscriptResponse,
        metadata: MeetingMetadataResponse,
        graph: GraphResponse,
        sections: frozenset[SectionId],
    ) -> str:
        chunks: list[str] = [self._render_header(meeting)]

        if SectionId.SUMMARY in sections and metadata.summary:
            chunks.append(self._render_summary(metadata.summary))
        if SectionId.DECISIONS in sections and metadata.decisions:
            chunks.append(self._render_decisions(metadata.decisions))
        if SectionId.ACTIONS in sections and metadata.action_items:
            chunks.append(self._render_action_items(metadata.action_items))
        if SectionId.QUESTIONS in sections and metadata.open_questions:
            chunks.append(self._render_open_questions(metadata.open_questions))
        if SectionId.TOPICS in sections and metadata.topics:
            chunks.append(self._render_topics(metadata.topics))
        if SectionId.GRAPH in sections and (graph.nodes or graph.edges):
            chunks.append(self._render_graph(graph, sections))
        if SectionId.SPEAKERS in sections and transcript.utterances:
            chunks.append(self._render_speakers(transcript.participants, transcript.utterances))
        if SectionId.TRANSCRIPT in sections and transcript.utterances:
            chunks.append(
                self._render_transcript(
                    transcript.participants,
                    transcript.utterances,
                    with_timings=SectionId.TIMINGS in sections,
                    with_confidence=SectionId.CONFIDENCE in sections,
                )
            )

        return "\n\n".join(chunks).rstrip() + "\n"

    @classmethod
    def _render_header(cls, meeting: Meeting) -> str:
        started = cls._fmt_datetime(meeting.started_at)
        ended = cls._fmt_datetime(meeting.ended_at) if meeting.ended_at else "—"
        duration = cls._fmt_duration(meeting.started_at, meeting.ended_at)
        return f"# {meeting.title}\n{started} → {ended} · {duration}"

    @staticmethod
    def _render_summary(summary: str) -> str:
        return f"## Summary\n\n{summary.strip()}"

    @classmethod
    def _render_decisions(cls, items: list[DecisionProjection]) -> str:
        lines = ["## Decisions", ""]
        for item in items:
            owner = f" — {item.owner_name}" if item.owner_name else ""
            timing = f" — t={cls._fmt_seconds(item.source_t_start)}" if item.source_t_start is not None else ""
            lines.append(f"- {item.text}{owner}{timing}")
        return "\n".join(lines)

    @classmethod
    def _render_action_items(cls, items: list[ActionItemProjection]) -> str:
        lines = ["## Action items", ""]
        for item in items:
            owner = item.owner_name or "unassigned"
            due = item.due_date or "—"
            timing = f" — t={cls._fmt_seconds(item.source_t_start)}" if item.source_t_start is not None else ""
            lines.append(f"- [ ] {item.text} — owner: {owner} — due {due}{timing}")
        return "\n".join(lines)

    @classmethod
    def _render_open_questions(cls, items: list[OpenQuestionProjection]) -> str:
        lines = ["## Open questions", ""]
        for item in items:
            timing = f", t={cls._fmt_seconds(item.source_t_start)}" if item.source_t_start is not None else ""
            lines.append(f"- {item.text} (status: {item.status}{timing})")
        return "\n".join(lines)

    @staticmethod
    def _render_topics(items: list[TopicProjection]) -> str:
        lines = ["## Topics", ""]
        for item in items:
            summary = f" — {item.summary}" if item.summary else ""
            lines.append(f"- **{item.name}**{summary}")
        return "\n".join(lines)

    @classmethod
    def _render_graph(cls, graph: GraphResponse, sections: frozenset[SectionId]) -> str:
        lines = ["## Knowledge graph", ""]
        nodes_by_type: dict[NodeType, list[GraphNodeResponse]] = defaultdict(list)
        skip_types = cls._graph_types_rendered_elsewhere(sections)
        for node in graph.nodes:
            if node.type in skip_types:
                continue

            nodes_by_type[node.type].append(node)

        type_order: list[NodeType] = [
            NodeType.PERSON,
            NodeType.TOPIC,
            NodeType.ENTITY,
            NodeType.DECISION,
            NodeType.ACTION_ITEM,
            NodeType.OPEN_QUESTION,
            NodeType.MEETING,
            NodeType.UTTERANCE,
        ]
        for node_type in type_order:
            bucket = nodes_by_type.get(node_type)
            if not bucket:
                continue

            lines.append(f"### {node_type.value} ({len(bucket)})")
            for node in bucket:
                label = cls._node_label(node)
                lines.append(f"- {label} (status: {node.status})")
            lines.append("")

        if graph.edges:
            lines.append(f"### Edges ({len(graph.edges)})")
            label_by_id: dict[UUID, str] = {n.id: cls._node_label(n) for n in graph.nodes}
            for edge in graph.edges:
                lines.append(
                    f"- {cls._edge_endpoint(edge.from_id, label_by_id)} —[{edge.type}]→ "
                    f"{cls._edge_endpoint(edge.to_id, label_by_id)}"
                )
            lines.append("")

        return "\n".join(lines).rstrip()

    @staticmethod
    def _graph_types_rendered_elsewhere(sections: frozenset[SectionId]) -> set[NodeType]:
        mapping = {
            SectionId.DECISIONS: NodeType.DECISION,
            SectionId.ACTIONS: NodeType.ACTION_ITEM,
            SectionId.QUESTIONS: NodeType.OPEN_QUESTION,
            SectionId.TOPICS: NodeType.TOPIC,
        }
        return {node_type for section, node_type in mapping.items() if section in sections}

    @staticmethod
    def _node_label(node: GraphNodeResponse) -> str:
        for key in ("text", "title", "name", "summary"):
            value = node.fields.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return f"{node.type.value} {node.id}"

    @staticmethod
    def _edge_endpoint(node_id: UUID, label_by_id: dict[UUID, str]) -> str:
        return label_by_id.get(node_id, str(node_id))

    @staticmethod
    def _render_speakers(participants: list[ParticipantResponse], utterances: list[UtteranceResponse]) -> str:
        counts: dict[UUID, int] = defaultdict(int)
        seconds: dict[UUID, float] = defaultdict(float)
        for u in utterances:
            counts[u.participant_id] += 1
            seconds[u.participant_id] += max(0.0, u.t_end - u.t_start)

        name_by_id = {p.id: p.name for p in participants}
        lines = ["## Speaker breakdown", ""]
        ordered = sorted(counts.items(), key=lambda kv: -seconds[kv[0]])
        for pid, count in ordered:
            name = name_by_id.get(pid, "Unknown")
            lines.append(f"- {name}: {count} utterances, {seconds[pid]:.0f}s total")
        return "\n".join(lines)

    @classmethod
    def _render_transcript(
        cls,
        participants: list[ParticipantResponse],
        utterances: list[UtteranceResponse],
        with_timings: bool,
        with_confidence: bool,
    ) -> str:
        name_by_id = {p.id: p.name for p in participants}
        lines = ["## Transcript", ""]
        for u in utterances:
            speaker = name_by_id.get(u.participant_id, "Unknown")
            timing = f" [{cls._fmt_seconds(u.t_start)}]" if with_timings else ""
            confidence = f" (c={u.confidence:.2f})" if with_confidence and u.confidence is not None else ""
            lines.append(f"**{speaker}**{timing} {u.text}{confidence}")
            lines.append("")
        return "\n".join(lines).rstrip()

    @staticmethod
    def _fmt_datetime(value: datetime) -> str:
        return value.strftime("%Y-%m-%d %H:%M UTC")

    @staticmethod
    def _fmt_duration(started: datetime, ended: datetime | None) -> str:
        if not ended:
            return "live"
        total = int((ended - started).total_seconds())
        minutes, seconds = divmod(total, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}h {minutes}m"
        return f"{minutes}m {seconds}s"

    @staticmethod
    def _fmt_seconds(value: float | None) -> str:
        if value is None:
            return "0:00"
        total = int(value)
        minutes, seconds = divmod(total, 60)
        return f"{minutes}:{seconds:02d}"
