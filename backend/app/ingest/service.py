from __future__ import annotations

import asyncio
import json
from uuid import UUID

import structlog
from fastapi import WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.ingest.client import MinioClient
from app.ingest.constants import INIT_VOICE_TIMEOUT
from app.ingest.schemas import CONTROL_ADAPTER, StreamInitMessage
from app.ingest.wav_writer import WavWriter
from app.meeting.models import Meeting

logger = structlog.get_logger()


class IngestService:
    def __init__(self, session: AsyncSession, minio_client: MinioClient) -> None:
        self._session = session
        self._minio_client = minio_client

    async def does_meeting_exist(self, meeting_id: UUID) -> bool:
        result = await self._session.exec(select(Meeting.id).where(Meeting.id == meeting_id))
        return result.one_or_none() is not None

    async def open_writer(self, meeting_id: UUID, stream_id: UUID) -> WavWriter:
        primary_key = self._minio_client.get_stream_object_key(meeting_id, stream_id)
        part = 2 if await self._minio_client.object_exists(primary_key) else 1
        return WavWriter(self._minio_client, self._minio_client.get_stream_object_key(meeting_id, stream_id, part))

    async def handle_stream(self, ws: WebSocket, meeting_id: UUID, stream_id: UUID) -> None:
        await ws.accept()

        first_message = await self._validate_connection(ws, meeting_id, stream_id)
        if first_message is None:
            return

        speaker_name = first_message.speaker.display_name or "(unnamed)"
        if not first_message.speaker.display_name:
            logger.warning("Speaker display name is empty in init payload", stream_id=stream_id)

        writer = await self.open_writer(meeting_id, stream_id)
        logger.debug(
            "Audio stream started",
            meeting_id=meeting_id,
            stream_id=stream_id,
            speaker=speaker_name,
            is_local_user=first_message.speaker.is_local_user,
            object_key=writer.key,
        )

        await self._consume_stream(ws, writer, meeting_id, stream_id, speaker_name)

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

    async def _consume_stream(
        self,
        ws: WebSocket,
        writer: WavWriter,
        meeting_id: UUID,
        stream_id: UUID,
        speaker_name: str,
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
                    speaker=speaker_name,
                    message=control_message.model_dump(),
                )
                if control_message.type == "speaker_renamed":
                    speaker_name = control_message.new_name or speaker_name

                elif control_message.type == "discard":
                    discarded = True
                    discard_reason = control_message.reason
                    break

                elif control_message.type == "stream_end":
                    break

        except WebSocketDisconnect:
            pass
        finally:
            await self._finalise(writer, meeting_id, stream_id, speaker_name, discarded, discard_reason)
            await ws.close()

    @classmethod
    async def _finalise(
        cls,
        writer: WavWriter,
        meeting_id: UUID,
        stream_id: UUID,
        speaker_name: str,
        discarded: bool,
        discard_reason: str | None,
    ) -> None:
        if discarded:
            writer.abort()
            logger.debug(
                "Audio stream discarded by the client",
                meeting_id=meeting_id,
                stream_id=stream_id,
                speaker=speaker_name,
                reason=discard_reason,
            )
            return

        audio_byte_count = await writer.close()
        logger.debug(
            "Audio stream ended and persisted",
            meeting_id=meeting_id,
            stream_id=stream_id,
            speaker=speaker_name,
            audio_byte_count=audio_byte_count,
            duration_seconds=round(writer.duration_seconds, 2),
            object_key=writer.key,
        )
