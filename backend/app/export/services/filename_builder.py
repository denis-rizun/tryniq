import re

from app.meeting.models import Meeting


class FilenameBuilder:
    @classmethod
    def build(cls, meeting: Meeting) -> str:
        slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", meeting.title.strip()).strip("-").lower()
        return f"{slug or 'meeting'}.md"
