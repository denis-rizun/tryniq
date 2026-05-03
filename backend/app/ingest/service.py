import asyncio
import json
from uuid import UUID

import structlog
from fastapi import WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.asr.clients.live import LiveASRClient
from app.config import config
from app.ingest.client import minio_client
from app.ingest.constants import INIT_VOICE_TIMEOUT
from app.ingest.schemas import CONTROL_ADAPTER, StreamInitMessage
from app.ingest.wav_writer import WavWriter
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

    async def does_meeting_exist(self, meeting_id: UUID) -> bool:
        result = await self._session.exec(select(Meeting.id).where(Meeting.id == meeting_id))
        return result.one_or_none() is not None

    async def open_writer(self, meeting_id: UUID, stream_id: UUID) -> WavWriter:
        primary_key = minio_client.get_stream_object_key(meeting_id, stream_id)
        part = 2 if await minio_client.object_exists(primary_key) else 1
        return WavWriter(minio_client.get_stream_object_key(meeting_id, stream_id, part))

    async def handle_stream(self, ws: WebSocket, meeting_id: UUID, stream_id: UUID) -> None:
        await ws.accept()

        first_message = await self._validate_connection(ws, meeting_id, stream_id)
        if first_message is None:
            return

        speaker = first_message.speaker
        participant = await self._try_create_participant(
            meeting_id=meeting_id,
            stream_id=stream_id,
            display_name=speaker.display_name,
            is_local_user=speaker.is_local_user,
        )

        writer = await self.open_writer(meeting_id, stream_id)
        logger.debug(
            "Audio stream started",
            meeting_id=meeting_id,
            stream_id=stream_id,
            speaker=speaker.display_name or "(unresolved)",
            is_local_user=speaker.is_local_user,
            object_key=writer.key,
            has_participant=participant is not None,
        )

        if config.asr.LIVE_ENABLED:
            await self._assign_swift_worker(
                meeting_id=meeting_id,
                stream_id=stream_id,
                participant_id=participant.id if participant else None,
                display_name=speaker.display_name,
                is_local_user=speaker.is_local_user,
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

        if not await self.does_meeting_exist(meeting_id):
            logger.warning("Meeting referenced by the WebSocket does not exist", meeting_id=meeting_id)
            await ws.close(code=status.WS_1008_POLICY_VIOLATION)
            return None

        return first_message

    async def _consume_stream(  # noqa: C901
        self,
        ws: WebSocket,
        writer: WavWriter,
        meeting_id: UUID,
        stream_id: UUID,
        is_local_user: bool,
        participant: Participant | None,
    ) -> None:
        discarded = False
        discard_reason: str | None = None
        try:
            while True:
                frame = await ws.receive()
                if frame.get("type") == "websocket.disconnect":
                    break

                if (audio_chunk := frame.get("bytes")) is not None:
                    writer.append(audio_chunk)
                    if config.asr.LIVE_ENABLED:
                        await self._live_asr_client.forward_audio_chunk(stream_id, audio_chunk)
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

                if control_message.type == "speaker_renamed":
                    participant = await self._handle_rename(
                        participant=participant,
                        meeting_id=meeting_id,
                        stream_id=stream_id,
                        new_name=control_message.new_name,
                        is_local_user=is_local_user,
                    )

                elif control_message.type == "discard":
                    discarded = True
                    discard_reason = control_message.reason
                    break

                elif control_message.type == "stream_end":
                    break

        except WebSocketDisconnect:
            pass
        finally:
            await self._finalise(writer, stream_id, participant, discarded, discard_reason)
            await ws.close()

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
    ) -> None:
        try:
            assigned = await self._live_asr_client.assign_stream(
                meeting_id=meeting_id,
                stream_id=stream_id,
                participant_id=participant_id,
                display_name=display_name,
                is_local_user=is_local_user,
            )
            if assigned is None:
                logger.info(
                    "live_asr: no swift worker connected; live transcript disabled for stream",
                    stream_id=str(stream_id),
                )
        except Exception as e:
            logger.warning("live_asr: assign_stream failed", error=str(e), stream_id=str(stream_id))

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
            except Exception as e:
                logger.debug("live_asr: close_stream failed", error=str(e), stream_id=str(stream_id))
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
