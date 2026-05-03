import struct
from enum import StrEnum

AUDIO_FRAME_HEADER_FMT = "<II"
AUDIO_FRAME_HEADER_LEN = struct.calcsize(AUDIO_FRAME_HEADER_FMT)
AUDIO_QUEUE_MAXSIZE = 100
DROP_WARN_INTERVAL_S = 5.0


class EventKind(StrEnum):
    HELLO = "hello"
    STREAM_OPEN = "stream_open"
    STREAM_CLOSE = "stream_close"
    PARTIAL = "partial"
    FINAL = "final"
    PING = "ping"
