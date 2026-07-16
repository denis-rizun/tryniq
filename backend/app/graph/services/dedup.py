from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import config
from app.core.client import get_ai_client
from app.graph.constants import NodeType
from app.graph.models import GraphNode
from app.graph.schemas import AddNodeOperation


class GraphNodeDeduplicator:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def batch_embeddings(self, operations: list[AddNodeOperation]) -> list[list[float] | None]:
        texts = [self._node_text(operation.fields) for operation in operations]
        indices = [index for index, text in enumerate(texts) if text]
        if not indices:
            return [None] * len(operations)

        vectors = await get_ai_client().embed([texts[index] for index in indices])
        embeddings: list[list[float] | None] = [None] * len(operations)
        for index, vector in zip(indices, vectors, strict=True):
            embeddings[index] = vector
        return embeddings

    async def dedup_node(self, meeting_id: UUID, node_type: NodeType, embedding: list[float]) -> GraphNode | None:
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
        return candidate if similarity >= config.graph.DEDUP_COSINE_THRESHOLD else None

    @staticmethod
    def _node_text(fields: dict) -> str:
        for key in ("text", "title", "summary", "name"):
            value = fields.get(key)
            if isinstance(value, str) and value.strip():
                return value

        return ""


def _cosine_distance(first: list[float], second: list[float]) -> float:
    dot = sum(left * right for left, right in zip(first, second, strict=False))
    first_norm = sum(value * value for value in first) ** 0.5
    second_norm = sum(value * value for value in second) ** 0.5
    if first_norm == 0 or second_norm == 0:
        return 1.0

    return 1.0 - dot / (first_norm * second_norm)
