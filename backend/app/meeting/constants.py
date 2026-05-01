import re
from enum import StrEnum


class MeetingStatus(StrEnum):
    LIVE = "live"
    FINALIZING = "finalizing"
    FINAL = "final"
    FAILED = "failed"


MEET_CODE_RE = re.compile(r"([a-z]{3}-[a-z]{4}-[a-z]{3})")
