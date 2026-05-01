from uuid import UUID

from app.asr.service import ASRService
from app.tasks import broker


@broker.task(retry_on_error=True, max_retries=2)
async def transcribe_final(meeting_id: str, stream_id: str) -> None:
    service = ASRService()
    await service.run(UUID(meeting_id), UUID(stream_id))
