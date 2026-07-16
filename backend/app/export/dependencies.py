from typing import Annotated

from fastapi import Depends

from app.db import SessionDep
from app.export.services.export import ExportService
from app.export.services.filename_builder import FilenameBuilder
from app.export.services.markdown_renderer import MarkdownRenderer
from app.graph.dependencies import build_graph_service
from app.metadata.dependencies import build_metadata_service
from app.transcript.service import TranscriptService


def get_export_service(session: SessionDep) -> ExportService:
    return ExportService(
        transcript_service=TranscriptService(session),
        metadata_service=build_metadata_service(session),
        graph_service=build_graph_service(session),
        markdown_render=MarkdownRenderer(),
        filename_builder=FilenameBuilder(),
    )


ExportServiceDep = Annotated[ExportService, Depends(get_export_service)]
