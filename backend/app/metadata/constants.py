from app.graph.constants import NODE_STATUS_VALUES, NodeType

GENERATED_NODE_TYPES = (
    NodeType.DECISION,
    NodeType.ACTION_ITEM,
    NodeType.OPEN_QUESTION,
    NodeType.TOPIC,
    NodeType.ENTITY,
)

METADATA_JSON_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "topics", "decisions", "action_items", "open_questions"],
    "properties": {
        "summary": {"type": "string"},
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["temp_id", "title", "summary"],
                "properties": {
                    "temp_id": {"type": "string"},
                    "title": {"type": "string"},
                    "summary": {"type": ["string", "null"]},
                },
            },
        },
        "decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "temp_id",
                    "text",
                    "status",
                    "source_utterance_refs",
                    "topic_refs",
                    "decided_by_person_ref",
                ],
                "properties": {
                    "temp_id": {"type": "string"},
                    "text": {"type": "string"},
                    "status": {"type": "string", "enum": NODE_STATUS_VALUES},
                    "source_utterance_refs": {"type": "array", "items": {"type": "string"}},
                    "topic_refs": {"type": "array", "items": {"type": "string"}},
                    "decided_by_person_ref": {"type": ["string", "null"]},
                },
            },
        },
        "action_items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "temp_id",
                    "text",
                    "due_date",
                    "status",
                    "source_utterance_refs",
                    "topic_refs",
                    "assignee_person_ref",
                ],
                "properties": {
                    "temp_id": {"type": "string"},
                    "text": {"type": "string"},
                    "due_date": {"type": ["string", "null"]},
                    "status": {"type": "string", "enum": NODE_STATUS_VALUES},
                    "source_utterance_refs": {"type": "array", "items": {"type": "string"}},
                    "topic_refs": {"type": "array", "items": {"type": "string"}},
                    "assignee_person_ref": {"type": ["string", "null"]},
                },
            },
        },
        "open_questions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["temp_id", "text", "status", "source_utterance_refs", "topic_refs"],
                "properties": {
                    "temp_id": {"type": "string"},
                    "text": {"type": "string"},
                    "status": {"type": "string", "enum": NODE_STATUS_VALUES},
                    "source_utterance_refs": {"type": "array", "items": {"type": "string"}},
                    "topic_refs": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
}
