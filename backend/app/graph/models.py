from datetime import UTC, datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.core.database import IDMixin
from app.graph.constants import EMBEDDING_DIM, EdgeType, NodeStatus, NodeType


class GraphNode(IDMixin, SQLModel, table=True):
    __tablename__ = "graph_node"

    meeting_id: UUID = Field(foreign_key="meeting.id", index=True)
    type: NodeType = Field(index=True)
    fields: dict = Field(sa_column=Column(JSONB, nullable=False))
    status: NodeStatus = Field(default=NodeStatus.PROVISIONAL)
    embedding: list[float] | None = Field(default=None, sa_column=Column(Vector(EMBEDDING_DIM), nullable=True))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        sa_type=DateTime(timezone=True),
        nullable=False,
    )


class GraphEdge(IDMixin, SQLModel, table=True):
    __tablename__ = "graph_edge"

    meeting_id: UUID = Field(foreign_key="meeting.id", index=True)
    type: EdgeType = Field(index=True)
    from_id: UUID = Field(foreign_key="graph_node.id", index=True)
    to_id: UUID = Field(foreign_key="graph_node.id", index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        sa_type=DateTime(timezone=True),
        nullable=False,
    )
