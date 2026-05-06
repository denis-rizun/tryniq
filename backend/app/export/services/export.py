import re
from dataclasses import dataclass

from app.export.constants import DEFAULT_SECTIONS, MEDIA_TYPE, SectionId
from app.export.services.md_render import MarkdownRenderer
from app.graph.service import GraphService
from app.meeting.models import Meeting
from app.metadata.services.orchestrator import MetadataService
from app.transcript.service import TranscriptService


@dataclass(frozen=True)
class MarkdownExport:
    body: str
    filename: str
    media_type: str


class FilenameBuilder:
    @classmethod
    def build(cls, meeting: Meeting) -> str:
        slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", meeting.title.strip()).strip("-").lower()
        return f"{slug or 'meeting'}.md"


class ExportService:
    def __init__(
        self,
        transcript_service: TranscriptService,
        metadata_service: MetadataService,
        graph_service: GraphService,
        markdown_render: MarkdownRenderer,
        filename_builder: FilenameBuilder,
    ) -> None:
        self.transcript_service = transcript_service
        self.metadata_service = metadata_service
        self.graph_service = graph_service
        self.markdown_render = markdown_render
        self.filename_builder = filename_builder

    async def export_markdown(self, meeting: Meeting, include: str | None) -> MarkdownExport:
        sections = self._parse_include(include)
        transcript = await self.transcript_service.get_transcript(meeting)
        metadata = await self.metadata_service.get_meeting_metadata(meeting.id)
        graph = await self.graph_service.get_graph(meeting.id)
        body = self.markdown_render.render(meeting, transcript, metadata, graph, sections)
        return MarkdownExport(
            body=body,
            filename=self.filename_builder.build(meeting),
            media_type=MEDIA_TYPE,
        )

    @staticmethod
    def _parse_include(raw: str | None) -> frozenset[SectionId]:
        if raw is None:
            return DEFAULT_SECTIONS
        parts = (p.strip() for p in raw.split(","))
        return frozenset(SectionId(p) for p in parts if p in SectionId._value2member_map_)
