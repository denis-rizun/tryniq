import asyncio
import json
import time
from datetime import UTC, datetime
from uuid import UUID

import structlog
from fastapi import WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.asr.clients.live import LiveASRClient
from app.config import config
from app.ingest.clients.minio import minio_client
from app.ingest.clients.wav_writer import WavWriter
from app.ingest.constants import BYTES_PER_SAMPLE, INIT_VOICE_TIMEOUT, SAMPLE_RATE
from app.ingest.schemas import CONTROL_ADAPTER, ControlMessage, StreamInitMessage
from app.meeting.models import Meeting
from app.participant.exceptions import ParticipantNameUnresolvedError
from app.participant.models import Participant
from app.participant.service import ParticipantService

logger = structlog.get_logger()


class IngestService:
    def __init__(
        self,
        session: AsyncSession,
        participant_service: ParticipantService,
        live_asr_client: LiveASRClient,
    ) -> None:
        self._session = session
        self._participant_service = participant_service
        self._live_asr_client = live_asr_client

    async def get_meeting(self, meeting_id: UUID) -> Meeting | None:
        result = await self._session.exec(select(Meeting).where(Meeting.id == meeting_id))
        return result.one_or_none()

    async def open_writer(self, meeting_id: UUID, stream_id: UUID) -> tuple[WavWriter, bool]:
        primary_key = minio_client.get_stream_object_key(meeting_id, stream_id)
        is_continuation = await minio_client.object_exists(primary_key)
        part = 2 if is_continuation else 1
        return WavWriter(minio_client.get_stream_object_key(meeting_id, stream_id, part)), is_continuation

    async def handle_stream(self, ws: WebSocket, meeting_id: UUID, stream_id: UUID) -> None:
        await ws.accept()

        first_message = await self._validate_connection(ws, meeting_id, stream_id)
        if first_message is None:
            return

        meeting = await self.get_meeting(meeting_id)
        if meeting is None:
            await ws.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        speaker = first_message.speaker
        participant = await self._try_create_participant(
            meeting_id=meeting_id,
            stream_id=stream_id,
            display_name=speaker.display_name,
            is_local_user=speaker.is_local_user,
        )

        writer, is_continuation = await self.open_writer(meeting_id, stream_id)
        stream_offset_seconds = (
            0.0 if is_continuation else max(0.0, (datetime.now(tz=UTC) - meeting.started_at).total_seconds())
        )
        offset_bytes = int(stream_offset_seconds * SAMPLE_RATE) * BYTES_PER_SAMPLE
        if offset_bytes > 0:
            writer.append(b"\x00" * offset_bytes)

        logger.debug(
            "Audio stream started",
            meeting_id=meeting_id,
            stream_id=stream_id,
            speaker=speaker.display_name or "(unresolved)",
            is_local_user=speaker.is_local_user,
            object_key=writer.key,
            has_participant=participant is not None,
            stream_offset_seconds=round(stream_offset_seconds, 3),
        )

        if config.asr.LIVE_ENABLED:
            await self._assign_swift_worker(
                meeting_id=meeting_id,
                stream_id=stream_id,
                participant_id=participant.id if participant else None,
                display_name=speaker.display_name,
                is_local_user=speaker.is_local_user,
                stream_offset_seconds=stream_offset_seconds,
            )
        else:
            logger.info("live_asr: disabled by ASR_LIVE_ENABLED=false", stream_id=str(stream_id))

        await self._consume_stream(
            ws=ws,
            writer=writer,
            meeting_id=meeting_id,
            stream_id=stream_id,
            is_local_user=speaker.is_local_user,
            participant=participant,
            offset_bytes=offset_bytes,
        )

    async def _try_create_participant(
        self,
        meeting_id: UUID,
        stream_id: UUID,
        display_name: str,
        is_local_user: bool,
    ) -> Participant | None:
        try:
            return await self._participant_service.create(
                meeting_id=meeting_id,
                stream_id=stream_id,
                display_name=display_name,
                is_local_user=is_local_user,
            )
        except ParticipantNameUnresolvedError:
            logger.debug(
                "Participant deferred — name unresolved at init; awaiting speaker_renamed",
                stream_id=stream_id,
            )
            return None

    async def _validate_connection(self, ws: WebSocket, meeting_id: UUID, stream_id: UUID) -> StreamInitMessage | None:
        try:
            raw_payload = await asyncio.wait_for(ws.receive_text(), timeout=INIT_VOICE_TIMEOUT)
        except (TimeoutError, WebSocketDisconnect):
            logger.warning(
                "Client did not send the init payload before the timeout",
                meeting_id=meeting_id,
                stream_id=stream_id,
                timeout_seconds=INIT_VOICE_TIMEOUT,
            )
            await ws.close(code=status.WS_1008_POLICY_VIOLATION)
            return None

        try:
            first_message = StreamInitMessage.model_validate_json(raw_payload)
        except ValidationError as e:
            logger.warning("Init payload does not match the expected schema", error=str(e))
            await ws.close(code=status.WS_1008_POLICY_VIOLATION)
            return None

        if first_message.meeting_id != meeting_id or first_message.stream_id != stream_id:
            logger.warning(
                "Init payload identifiers do not match the WebSocket URL",
                url_meeting_id=meeting_id,
                init_meeting_id=first_message.meeting_id,
                url_stream_id=stream_id,
                init_stream_id=first_message.stream_id,
            )
            await ws.close(code=status.WS_1008_POLICY_VIOLATION)
            return None

        if await self.get_meeting(meeting_id) is None:
            logger.warning("Meeting referenced by the WebSocket does not exist", meeting_id=meeting_id)
            await ws.close(code=status.WS_1008_POLICY_VIOLATION)
            return None

        return first_message

    async def _consume_stream(
        self,
        ws: WebSocket,
        writer: WavWriter,
        meeting_id: UUID,
        stream_id: UUID,
        is_local_user: bool,
        participant: Participant | None,
        offset_bytes: int,
    ) -> None:
        discarded = False
        discard_reason: str | None = None
        stream_started_monotonic = time.monotonic()
        streamer_bytes_sent = 0
        try:
            while True:
                frame = await ws.receive()
                if frame.get("type") == "websocket.disconnect":
                    break

                if (audio_chunk := frame.get("bytes")) is not None:
                    streamer_bytes_sent = await self._forward_audio(
                        writer, stream_id, audio_chunk, offset_bytes, stream_started_monotonic, streamer_bytes_sent
                    )
                    continue

                if (raw_control_payload := frame.get("text")) is None:
                    continue

                try:
                    control_message = CONTROL_ADAPTER.validate_python(json.loads(raw_control_payload))
                except (ValidationError, json.JSONDecodeError) as e:
                    logger.warning(
                        "Received an unrecognised control message",
                        error=str(e),
                        raw_payload=raw_control_payload[:200],
                    )
                    continue

                logger.debug(
                    "Received a control message",
                    stream_id=stream_id,
                    participant_id=participant.id if participant else None,
                    message=control_message.model_dump(),
                )

                participant, discarded, discard_reason, should_end = await self._handle_control_message(
                    control_message, participant, meeting_id, stream_id, is_local_user
                )
                if should_end:
                    break

        except WebSocketDisconnect:
            pass
        finally:
            await self._finalise(writer, stream_id, participant, discarded, discard_reason)
            await ws.close()

    async def _forward_audio(
        self,
        writer: WavWriter,
        stream_id: UUID,
        audio_chunk: bytes,
        offset_bytes: int,
        stream_started_monotonic: float,
        streamer_bytes_sent: int,
    ) -> int:
        elapsed_seconds = time.monotonic() - stream_started_monotonic
        elapsed_bytes = int(elapsed_seconds * SAMPLE_RATE) * BYTES_PER_SAMPLE
        writer.pad_silence_to(offset_bytes + elapsed_bytes - len(audio_chunk))
        writer.append(audio_chunk)
        if not config.asr.LIVE_ENABLED:
            return streamer_bytes_sent

        pad_needed = elapsed_bytes - streamer_bytes_sent - len(audio_chunk)
        if pad_needed > 0:
            await self._live_asr_client.forward_audio_chunk(stream_id, b"\x00" * pad_needed)
            streamer_bytes_sent += pad_needed
        await self._live_asr_client.forward_audio_chunk(stream_id, audio_chunk)
        return streamer_bytes_sent + len(audio_chunk)

    async def _handle_control_message(
        self,
        control_message: ControlMessage,
        participant: Participant | None,
        meeting_id: UUID,
        stream_id: UUID,
        is_local_user: bool,
    ) -> tuple[Participant | None, bool, str | None, bool]:
        if control_message.kind == "speaker_renamed":
            participant = await self._handle_rename(
                participant, meeting_id, stream_id, control_message.new_name, is_local_user
            )
            return participant, False, None, False
        if control_message.kind == "discard":
            return participant, True, control_message.reason, True
        return participant, False, None, control_message.kind == "stream_end"

    async def _handle_rename(
        self,
        participant: Participant | None,
        meeting_id: UUID,
        stream_id: UUID,
        new_name: str,
        is_local_user: bool,
    ) -> Participant | None:
        if not new_name:
            return participant
        try:
            return await self._participant_service.create(
                meeting_id=meeting_id,
                stream_id=stream_id,
                display_name=new_name,
                is_local_user=is_local_user,
            )
        except ParticipantNameUnresolvedError:
            return participant

    async def _assign_swift_worker(
        self,
        meeting_id: UUID,
        stream_id: UUID,
        participant_id: UUID | None,
        display_name: str | None,
        is_local_user: bool,
        stream_offset_seconds: float,
    ) -> None:
        try:
            assigned = await self._live_asr_client.assign_stream(
                meeting_id=meeting_id,
                stream_id=stream_id,
                participant_id=participant_id,
                display_name=display_name,
                is_local_user=is_local_user,
                stream_offset_seconds=stream_offset_seconds,
            )
            if assigned is None:
                logger.info(
                    "live_asr: no swift worker connected; live transcript disabled for stream",
                    stream_id=str(stream_id),
                )
        except (OSError, RuntimeError) as exc:
            logger.warning("live_asr: assign_stream failed", error=str(exc), stream_id=str(stream_id))

    async def _finalise(
        self,
        writer: WavWriter,
        stream_id: UUID,
        participant: Participant | None,
        discarded: bool,
        discard_reason: str | None,
    ) -> None:
        if config.asr.LIVE_ENABLED:
            try:
                await self._live_asr_client.close_stream(stream_id)
            except (OSError, RuntimeError) as exc:
                logger.debug("live_asr: close_stream failed", error=str(exc), stream_id=str(stream_id))
        participant_id = participant.id if participant else None
        if discarded:
            writer.abort()
            logger.debug(
                "Audio stream discarded by the client",
                stream_id=stream_id,
                participant_id=participant_id,
                reason=discard_reason,
            )
            return

        audio_byte_count = await writer.close()
        logger.debug(
            "Audio stream ended and persisted",
            stream_id=stream_id,
            participant_id=participant_id,
            audio_byte_count=audio_byte_count,
            duration_seconds=round(writer.duration_seconds, 2),
            object_key=writer.key,
        )
