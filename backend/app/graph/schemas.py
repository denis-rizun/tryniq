from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BeforeValidator, Field, TypeAdapter

from app.core.base_schema import BaseSchema
from app.graph.constants import EdgeType, GraphOperationKind, NodeStatus, NodeType
from app.meeting.constants import MeetingEventKind


def _without_nulls(value: object) -> object:
    if isinstance(value, dict):
        return {k: v for k, v in value.items() if v is not None}
    return value


NodeFields = Annotated[dict, BeforeValidator(_without_nulls)]


class AddNodeOperation(BaseSchema):
    kind: Literal[GraphOperationKind.ADD_NODE] = GraphOperationKind.ADD_NODE
    node_type: NodeType
    fields: NodeFields
    temp_id: str
    status: NodeStatus = NodeStatus.PROVISIONAL


class AddEdgeOperation(BaseSchema):
    model_config = {"populate_by_name": True}

    kind: Literal[GraphOperationKind.ADD_EDGE] = GraphOperationKind.ADD_EDGE
    edge_type: EdgeType
    from_ref: str = Field(alias="from")
    to_ref: str = Field(alias="to")


class UpdateNodeOperation(BaseSchema):
    kind: Literal[GraphOperationKind.UPDATE_NODE] = GraphOperationKind.UPDATE_NODE
    id: str
    fields: NodeFields | None = None
    status: NodeStatus | None = None


type GraphOperation = Annotated[AddNodeOperation | AddEdgeOperation | UpdateNodeOperation, Field(discriminator="kind")]
GRAPH_OPERATION_ADAPTER: TypeAdapter[GraphOperation] = TypeAdapter(GraphOperation)
GRAPH_OPERATIONS_ADAPTER: TypeAdapter[list[GraphOperation]] = TypeAdapter(list[GraphOperation])


class GraphOperationsResponse(BaseSchema):
    ops: list[GraphOperation] = Field(default_factory=list)


class GraphNodeResponse(BaseSchema):
    id: UUID
    meeting_id: UUID
    type: NodeType
    fields: dict
    status: NodeStatus
    created_at: datetime


class GraphEdgeResponse(BaseSchema):
    id: UUID
    meeting_id: UUID
    type: EdgeType
    from_id: UUID
    to_id: UUID
    created_at: datetime


class GraphResponse(BaseSchema):
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]


class GraphPatchEvent(BaseSchema):
    kind: Literal[MeetingEventKind.GRAPH_PATCH] = MeetingEventKind.GRAPH_PATCH
    meeting_id: UUID
    added_nodes: list[GraphNodeResponse]
    added_edges: list[GraphEdgeResponse]
    updated_nodes: list[GraphNodeResponse]
    timestamp: datetime
