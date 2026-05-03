from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.asr.clients.live import LiveASRClient
from app.asr.services.live import LiveASRService
from app.participant.dependencies import ParticipantServiceDep
from app.transcript.dependencies import TranscriptServiceDep


@lru_cache(maxsize=1)
def get_live_asr_client() -> LiveASRClient:
    return LiveASRClient()


LiveASRClientDep = Annotated[LiveASRClient, Depends(get_live_asr_client)]


def get_live_asr_service(
    client: LiveASRClientDep,
    participant_service: ParticipantServiceDep,
    transcript_service: TranscriptServiceDep,
) -> LiveASRService:
    return LiveASRService(client, participant_service, transcript_service)


LiveASRServiceDep = Annotated[LiveASRService, Depends(get_live_asr_service)]
