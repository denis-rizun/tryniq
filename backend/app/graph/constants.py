from enum import StrEnum


class NodeType(StrEnum):
    MEETING = "Meeting"
    PERSON = "Person"
    TOPIC = "Topic"
    DECISION = "Decision"
    ACTION_ITEM = "ActionItem"
    OPEN_QUESTION = "OpenQuestion"
    ENTITY = "Entity"
    UTTERANCE = "Utterance"


class EdgeType(StrEnum):
    PARTICIPATED_IN = "PARTICIPATED_IN"
    DISCUSSED_IN = "DISCUSSED_IN"
    MADE_DECISION = "MADE_DECISION"
    ASSIGNED_TO = "ASSIGNED_TO"
    BLOCKS = "BLOCKS"
    ABOUT_TOPIC = "ABOUT_TOPIC"
    MENTIONS = "MENTIONS"
    SOURCE = "SOURCE"
    RELATES_TO = "RELATES_TO"


class NodeStatus(StrEnum):
    PROVISIONAL = "provisional"
    CONFIRMED = "confirmed"
    SUPERSEDED = "superseded"


class GraphOperationKind(StrEnum):
    ADD_NODE = "add_node"
    ADD_EDGE = "add_edge"
    UPDATE_NODE = "update_node"


GROUNDED_NODE_TYPES = frozenset({NodeType.DECISION, NodeType.ACTION_ITEM, NodeType.OPEN_QUESTION})
EMBEDDING_DIM = 1536

NODE_TYPE_VALUES = list(NodeType)
EDGE_TYPE_VALUES = list(EdgeType)
NODE_STATUS_VALUES = list(NodeStatus)

NODE_FIELDS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["title", "summary", "text", "due_date", "name"],
    "properties": {
        "title": {"type": ["string", "null"]},
        "summary": {"type": ["string", "null"]},
        "text": {"type": ["string", "null"]},
        "due_date": {"type": ["string", "null"]},
        "name": {"type": ["string", "null"]},
    },
}

GRAPH_OPS_JSON_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["ops"],
    "properties": {
        "ops": {
            "type": "array",
            "items": {
                "anyOf": [
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["op", "node_type", "fields", "temp_id", "status"],
                        "properties": {
                            "op": {"type": "string", "enum": [GraphOperationKind.ADD_NODE]},
                            "node_type": {"type": "string", "enum": NODE_TYPE_VALUES},
                            "fields": NODE_FIELDS_SCHEMA,
                            "temp_id": {"type": "string"},
                            "status": {"type": "string", "enum": NODE_STATUS_VALUES},
                        },
                    },
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["op", "edge_type", "from", "to"],
                        "properties": {
                            "op": {"type": "string", "enum": [GraphOperationKind.ADD_EDGE]},
                            "edge_type": {"type": "string", "enum": EDGE_TYPE_VALUES},
                            "from": {"type": "string"},
                            "to": {"type": "string"},
                        },
                    },
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["op", "id", "fields", "status"],
                        "properties": {
                            "op": {"type": "string", "enum": [GraphOperationKind.UPDATE_NODE]},
                            "id": {"type": "string"},
                            "fields": {"anyOf": [NODE_FIELDS_SCHEMA, {"type": "null"}]},
                            "status": {
                                "anyOf": [
                                    {"type": "string", "enum": NODE_STATUS_VALUES},
                                    {"type": "null"},
                                ],
                            },
                        },
                    },
                ],
            },
        },
    },
}
