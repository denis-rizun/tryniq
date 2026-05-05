from uuid import UUID

from app.graph.constants import EdgeType, NodeType
from app.graph.models import GraphEdge, GraphNode


class GraphIndex:
    def __init__(self, nodes: list[GraphNode], edges: list[GraphEdge]) -> None:
        self.nodes = nodes
        self.nodes_by_id = {n.id: n for n in nodes}
        self.out_edges: dict[UUID, list[GraphEdge]] = {}
        self.in_edges: dict[UUID, list[GraphEdge]] = {}
        for e in edges:
            self.out_edges.setdefault(e.from_id, []).append(e)
            self.in_edges.setdefault(e.to_id, []).append(e)

    def source(self, node_id: UUID) -> tuple[UUID | None, float | None]:
        for e in self.out_edges.get(node_id, []):
            if e.type != EdgeType.SOURCE:
                continue

            target = self.nodes_by_id.get(e.to_id)
            if not target or target.type != NodeType.UTTERANCE:
                continue

            fields = target.fields or {}
            return self._parse_uuid(fields.get("utterance_id")), self._parse_float(fields.get("t_start"))
        return None, None

    def topic_ids(self, node_id: UUID) -> list[UUID]:
        ids: list[UUID] = []
        for e in self.out_edges.get(node_id, []):
            if e.type != EdgeType.ABOUT_TOPIC:
                continue
            target = self.nodes_by_id.get(e.to_id)
            if target and target.type == NodeType.TOPIC:
                ids.append(target.id)
        return ids

    def owner(self, node_id: UUID, edge_type: EdgeType, direction: str) -> str | None:
        edges = self.out_edges.get(node_id, []) if direction == "out" else self.in_edges.get(node_id, [])
        for e in edges:
            if e.type != edge_type:
                continue

            other_id = e.to_id if direction == "out" else e.from_id
            target = self.nodes_by_id.get(other_id)
            if not target or target.type != NodeType.PERSON:
                continue

            name = (target.fields or {}).get("name")
            if isinstance(name, str) and name.strip():
                return name
        return None

    def related_meeting_ids(self, meeting_node_id: UUID) -> list[UUID]:
        ids: list[UUID] = []
        for e in self.out_edges.get(meeting_node_id, []):
            if e.type != EdgeType.RELATES_TO:
                continue

            target = self.nodes_by_id.get(e.to_id)
            if not target or target.type != NodeType.MEETING:
                continue

            other_id = self._parse_uuid((target.fields or {}).get("meeting_id"))
            if other_id:
                ids.append(other_id)
        return ids

    @staticmethod
    def _parse_uuid(value: object) -> UUID | None:
        if not value:
            return None
        try:
            return UUID(str(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_float(value: object) -> float | None:
        if isinstance(value, int | float):
            return float(value)
        return None
