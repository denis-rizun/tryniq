import re
from enum import StrEnum


class ChatScope(StrEnum):
    MEETING = "meeting"
    ALL = "all"


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatStreamEventKind(StrEnum):
    MESSAGE_STARTED = "message_started"
    TOKEN = "token"
    MESSAGE_COMPLETED = "message_completed"
    ERROR = "error"


CHAT_EMBEDDING_DIM = 1536
CHAT_TITLE_MAX_LEN = 80
CHAT_RETRIEVAL_GRAPH_TYPES: tuple[str, ...] = ("Decision", "ActionItem", "OpenQuestion", "Topic")
CROSS_LABEL_MAX_LEN = 40

REF_PATTERN = re.compile(r"\[(u\d+)\]")
GRAPH_REF_PATTERN = re.compile(r"\s*\[g\d+\]")


SCOPE_NOTE_MEETING = "You are answering about ONE specific meeting."
SCOPE_NOTE_ALL = "You are answering across MULTIPLE finalized meetings."
