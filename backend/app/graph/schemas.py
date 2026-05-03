from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, TypeAdapter

from app.core.base_schema import BaseSchema
from app.graph.constants import EdgeType, GraphOperationKind, NodeStatus, NodeType
from app.meeting.constants import MeetingEventKind


class AddNodeOperation(BaseSchema):
    op: Literal[GraphOperationKind.ADD_NODE] = GraphOperationKind.ADD_NODE
    node_type: NodeType
    fields: dict
    temp_id: str
    status: NodeStatus = NodeStatus.PROVISIONAL


class AddEdgeOperation(BaseSchema):
    model_config = {"populate_by_name": True}

    op: Literal[GraphOperationKind.ADD_EDGE] = GraphOperationKind.ADD_EDGE
    edge_type: EdgeType
    from_ref: str = Field(alias="from")
    to_ref: str = Field(alias="to")



class UpdateNodeOperation(BaseSchema):
    op: Literal[GraphOperationKind.UPDATE_NODE] = GraphOperationKind.UPDATE_NODE
    id: str
    fields: dict | None = None
    status: NodeStatus | None = None


type GraphOperation = Annotated[AddNodeOperation | AddEdgeOperation | UpdateNodeOperation, Field(discriminator="op")]
GRAPH_OPERATION_ADAPTER: TypeAdapter[GraphOperation] = TypeAdapter(GraphOperation)
GRAPH_OPERATIONS_ADAPTER: TypeAdapter[list[GraphOperation]] = TypeAdapter(list[GraphOperation])


class GraphNodeRead(BaseSchema):
    id: UUID
    meeting_id: UUID
    type: NodeType
    fields: dict
    status: NodeStatus
    created_at: datetime


class GraphEdgeRead(BaseSchema):
    id: UUID
    meeting_id: UUID
    type: EdgeType
    from_id: UUID
    to_id: UUID
    created_at: datetime


class GraphResponse(BaseSchema):
    nodes: list[GraphNodeRead]
    edges: list[GraphEdgeRead]


class GraphPatchEvent(BaseSchema):
    kind: Literal[MeetingEventKind.GRAPH_PATCH] = MeetingEventKind.GRAPH_PATCH
    meeting_id: UUID
    added_nodes: list[GraphNodeRead]
    added_edges: list[GraphEdgeRead]
    updated_nodes: list[GraphNodeRead]
    timestamp: datetime
