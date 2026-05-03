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
SYSTEM_PROMPT = """You extract a meeting knowledge graph from a window of transcribed utterances.
Return ONLY a JSON array of ops via the emit_graph_ops tool.

NODE TYPES (use the strict casing shown):
- Topic           — a subject of discussion. fields: {"title": str, "summary"?: str}
- Decision        — a concluded choice. fields: {"text": str}
- ActionItem      — a follow-up task. fields: {"text": str, "due_date"?: str}
- OpenQuestion    — an unresolved question. fields: {"text": str}
- Entity          — a thing/concept named explicitly. fields: {"name": str}
- Person          — a named human. fields: {"name": str}

EDGE TYPES — these are the ONLY allowed (from_type → to_type) directions:
- DISCUSSED_IN    : Topic → Meeting           (anchor every Topic to the meeting)
- ABOUT_TOPIC     : Decision|ActionItem|OpenQuestion → Topic
- ASSIGNED_TO     : ActionItem → Person
- MADE_DECISION   : Person → Decision
- BLOCKS          : OpenQuestion → Decision
- MENTIONS        : Utterance → Entity|Person
- SOURCE          : Decision|ActionItem|OpenQuestion → Utterance   (REQUIRED grounding)
- RELATES_TO      : Topic → Topic                                  (only if clearly related)

REFERENCE RULES:
- Each utterance in the window has a short token like [u01], [u02], … — use those tokens
  EXACTLY when referencing utterances. Do NOT invent or guess utterance ids.
- Refer to the meeting using the literal token "meeting".
- Refer to nodes you create in this turn by their temp_id ("n1", "n2", ...).
- Never emit UUIDs in your output.

EXTRACTION RULES:
1. Topics: prefer ONE consolidated topic over many small ones when the speech is one cohesive
   theme with sub-aspects. Only split when the speaker visibly changes subject.
2. Every Topic you add MUST have a DISCUSSED_IN edge to the meeting_id.
3. Every Decision / ActionItem / OpenQuestion MUST have a SOURCE edge to at least one real
   utterance UUID from the window. No SOURCE → drop the node.
4. Use MENTIONS (utterance → Entity/Person) when a person or named thing is referenced; do NOT
   use ABOUT_TOPIC for utterances. ABOUT_TOPIC is only for Decision/ActionItem/OpenQuestion → Topic.
5. ASSIGNED_TO only when ownership is explicit ("Mark, can you ..."). Do NOT invent owners.
6. Do NOT extract from hypothetical phrasing ("we could", "maybe", "what if").
7. Nodes start status="provisional". Promote to "confirmed" only on explicit affirmation
   ("let's do X", "agreed", "yes, do it"). Mark "superseded" only if explicitly contradicted.
8. If the window has only chit-chat (weather, off-topic), return an empty ops array.

EXAMPLE
Input window:
  meeting_ref = meeting
  [u01] participant=... alice: We should roll back the eu-west-1 deploy.
  [u02] participant=... bob:   Agreed. Mark, can you draft the postmortem?
  [u03] participant=... mark:  Yeah, I'll have it by Friday.

Correct ops:
[
  {"op":"add_node","node_type":"Topic","fields":{"title":"eu-west-1 rollback"},"temp_id":"t1"},
  {"op":"add_edge","edge_type":"DISCUSSED_IN","from":"t1","to":"meeting"},
  {"op":"add_node","node_type":"Decision","fields":{"text":"Roll back eu-west-1 deploy"},
   "temp_id":"d1","status":"confirmed"},
  {"op":"add_edge","edge_type":"SOURCE","from":"d1","to":"u01"},
  {"op":"add_edge","edge_type":"ABOUT_TOPIC","from":"d1","to":"t1"},
  {"op":"add_node","node_type":"Person","fields":{"name":"Mark"},"temp_id":"p_mark"},
  {"op":"add_node","node_type":"ActionItem","fields":{"text":"Draft postmortem","due_date":"Friday"},
   "temp_id":"a1","status":"confirmed"},
  {"op":"add_edge","edge_type":"SOURCE","from":"a1","to":"u02"},
  {"op":"add_edge","edge_type":"ABOUT_TOPIC","from":"a1","to":"t1"},
  {"op":"add_edge","edge_type":"ASSIGNED_TO","from":"a1","to":"p_mark"}
]
"""
TOOL_NAME = "emit_graph_ops"
TOOL_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "ops": {
            "type": "array",
            "items": {"type": "object"},
        },
    },
    "required": ["ops"],
}
ANTHROPIC_TOOL = {
    "name": TOOL_NAME,
    "description": "Emit a list of graph operations extracted from the window.",
    "input_schema": TOOL_PARAMETERS_SCHEMA,
}
MISTRAL_TOOL = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": "Emit a list of graph operations extracted from the window.",
        "parameters": TOOL_PARAMETERS_SCHEMA,
    },
}
