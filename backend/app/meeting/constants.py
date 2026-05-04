import re
from enum import StrEnum


class MeetingStatus(StrEnum):
    LIVE = "live"
    UPLOADING = "uploading"
    NORMALIZING = "normalizing"
    DIARIZING = "diarizing"
    TRANSCRIBING = "transcribing"
    FINALIZING = "finalizing"
    FINAL = "final"
    FAILED = "failed"


MEET_CODE_RE = re.compile(r"([a-z]{3}-[a-z]{4}-[a-z]{3})")
GLOBAL_LIFECYCLE_CHANNEL = "meetings:lifecycle"
EVENT_CHANNEL = "meeting:{meeting_id}:events"
PARTIAL_KEY = "live:partial:{stream_id}"
PARTIAL_TTL_SECONDS = 60
HEARTBEAT_INTERVAL_SECONDS = 15.0


class LifecycleEvent(StrEnum):
    STARTED = "started"
    ENDED = "ended"
    UPLOADING = "uploading"
    NORMALIZING = "normalizing"
    DIARIZING = "diarizing"
    TRANSCRIBING = "transcribing"
    FINALIZING = "finalizing"
    FINAL = "final"
    FAILED = "failed"


GLOBAL_LIFECYCLE_EVENTS = frozenset(
    {
        LifecycleEvent.STARTED,
        LifecycleEvent.ENDED,
        LifecycleEvent.UPLOADING,
        LifecycleEvent.FINAL,
        LifecycleEvent.FAILED,
    }
)


class MeetingEventKind(StrEnum):
    MEETING_LIFECYCLE = "meeting_lifecycle"
    PARTIAL_TRANSCRIPT = "partial_transcript"
    TRANSCRIPT_SEGMENT = "transcript_segment"
    GRAPH_PATCH = "graph_patch"
