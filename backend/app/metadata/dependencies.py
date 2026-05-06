from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.client import get_ai_client
from app.db import SessionDep
from app.graph.service import GraphService
from app.metadata.services.extractor import MetadataExtractor
from app.metadata.services.orchestrator import MetadataService
from app.metadata.services.reader import MetadataReader
from app.metadata.services.related_finder import RelatedMeetingsFinder
from app.metadata.services.writer import MetadataGraphWriter


def build_metadata_service(session: AsyncSession) -> MetadataService:
    ai_client = get_ai_client()
    graph_service = GraphService(session)
    return MetadataService(
        session=session,
        extractor=MetadataExtractor(ai_client),
        writer=MetadataGraphWriter(session, graph_service, ai_client),
        related_finder=RelatedMeetingsFinder(session),
        reader=MetadataReader(session),
    )


def get_metadata_service(session: SessionDep) -> MetadataService:
    return build_metadata_service(session)


MetadataServiceDep = Annotated[MetadataService, Depends(get_metadata_service)]
