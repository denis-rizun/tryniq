from uuid import UUID

import structlog

from app.db import async_session
from app.metadata.dependencies import build_metadata_service
from app.tasks import broker

logger = structlog.get_logger()


@broker.task(retry_on_error=True, max_retries=2)
async def extract_meeting_metadata(meeting_id: str) -> None:
    mid = UUID(meeting_id)
    async with async_session() as session:
        service = build_metadata_service(session)
        await service.extract_metadata(mid)
