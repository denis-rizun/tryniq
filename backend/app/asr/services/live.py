import json
from uuid import UUID

import structlog
from pydantic import ValidationError
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError
from starlette.websockets import WebSocket

from app.asr.clients.live import LiveASRClient
from app.asr.clients.worker_session import WorkerSession
from app.asr.constants import EventKind
from app.asr.schemas import (
    CLIENT_MESSAGE_ADAPTER,
    FinalTranscriptEvent,
    HandshakeEvent,
    PartialTranscriptEvent,
)
from app.core.decorators import suppress_ws_disconnect
from app.meeting.client import redis_client
from app.participant.service import ParticipantService
from app.transcript.service import TranscriptService

logger = structlog.get_logger()


class LiveASRService:
    def __init__(
        self,
        client: LiveASRClient,
        participant_service: ParticipantService,
        transcript_service: TranscriptService,
    ) -> None:
        self.client = client
        self.participant_service = participant_service
        self.transcript_service = transcript_service

    @suppress_ws_disconnect
    async def run_session(self, ws: WebSocket) -> None:
        await ws.accept()
        handshake = await self._read_handshake(ws)
        if handshake is None:
            return

        worker = await self.client.register_worker(ws, handshake.worker_id, handshake.capacity)
        try:
            await self._consume_worker_messages(ws, worker)
        except (RedisError, SQLAlchemyError):
            logger.exception("worker session error", worker_id=handshake.worker_id)
        finally:
            await self._flush_pending_segments(worker)
            await self.client.unregister_worker(worker)

    @staticmethod
    async def _read_handshake(ws: WebSocket) -> HandshakeEvent | None:
        raw = await ws.receive_text()
        try:
            return HandshakeEvent.model_validate_json(raw)
        except ValidationError as e:
            logger.warning("invalid handshake payload", error=str(e))
            await ws.close(code=1008)
            return None

    async def _consume_worker_messages(self, ws: WebSocket, worker: WorkerSession) -> None:
        while True:
            raw = await ws.receive_text()
            try:
                event = CLIENT_MESSAGE_ADAPTER.validate_python(json.loads(raw))
            except (ValidationError, json.JSONDecodeError) as e:
                logger.warning("invalid worker message", error=str(e), raw=raw[:200])
                continue

            if event.kind == EventKind.HELLO:
                logger.warning("unexpected handshake after connection established", worker_id=worker.worker_id)
                continue
            if event.kind == EventKind.PING:
                continue
            if event.kind == EventKind.PARTIAL:
                await self._handle_partial_transcript(worker, event)
            elif event.kind == EventKind.FINAL:
                await self._handle_final_transcript(worker, event)

    async def _handle_final_transcript(self, worker: WorkerSession, event: FinalTranscriptEvent) -> None:
        state = worker.streams.get(event.stream_id)
        if state is None:
            return

        state.last_partial_text = ""
        await self._persist_final_segment(
            meeting_id=state.meeting_id,
            stream_id=event.stream_id,
            participant_id=state.participant_id,
            text=event.text,
            t_start=event.t_start + state.stream_offset_seconds,
            t_end=event.t_end + state.stream_offset_seconds,
        )

    async def _flush_pending_segments(self, worker: WorkerSession) -> None:
        for state in worker.streams.values():
            if not state.last_partial_text:
                continue

            try:
                await self._persist_final_segment(
                    meeting_id=state.meeting_id,
                    stream_id=state.stream_id,
                    participant_id=state.participant_id,
                    text=state.last_partial_text,
                    t_start=0.0,
                    t_end=0.0,
                )
            except (RedisError, SQLAlchemyError):
                logger.exception("synthetic final failed", stream_id=state.stream_id)

    async def _persist_final_segment(
        self,
        meeting_id: UUID,
        stream_id: UUID,
        participant_id: UUID | None,
        text: str,
        t_start: float,
        t_end: float,
    ) -> UUID | None:
        if not text:
            return None

        if participant_id is None:
            participant = await self.participant_service.get_by_stream(meeting_id, stream_id)
            participant_id = participant.id if participant else None

        if participant_id is None:
            logger.warning("no participant for final, skipping persist", stream_id=stream_id)
            return None

        utterance = await self.transcript_service.create_live(
            meeting_id=meeting_id,
            participant_id=participant_id,
            stream_id=stream_id,
            text=text,
            t_start=t_start,
            t_end=t_end,
        )
        if utterance is None:
            return None

        await redis_client.publish_transcript_segment(
            meeting_id=meeting_id,
            stream_id=stream_id,
            participant_id=participant_id,
            utterance_id=utterance.id,
            text=text,
            t_start=t_start,
            t_end=t_end,
            is_final=False,
        )
        return utterance.id

    @staticmethod
    async def _handle_partial_transcript(worker: WorkerSession, event: PartialTranscriptEvent) -> None:
        state = worker.streams.get(event.stream_id)
        if state is None:
            return

        state.last_partial_text = event.text
        if not event.text:
            return

        await redis_client.publish_partial_transcript(
            meeting_id=state.meeting_id, stream_id=event.stream_id, participant_id=state.participant_id, text=event.text
        )
