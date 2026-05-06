from typing import Annotated

from fastapi import Depends

from app.db import SessionDep
from app.export.services.export import ExportService, FilenameBuilder
from app.export.services.md_render import MarkdownRenderer
from app.graph.service import GraphService
from app.metadata.dependencies import build_metadata_service
from app.transcript.service import TranscriptService


def get_export_service(session: SessionDep) -> ExportService:
    return ExportService(
        transcript_service=TranscriptService(session),
        metadata_service=build_metadata_service(session),
        graph_service=GraphService(session),
        markdown_render=MarkdownRenderer(),
        filename_builder=FilenameBuilder(),
    )


ExportServiceDep = Annotated[ExportService, Depends(get_export_service)]
