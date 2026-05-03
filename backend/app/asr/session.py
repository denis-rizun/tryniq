import asyncio
import struct
import time
from uuid import UUID

import structlog
from fastapi import WebSocket, WebSocketDisconnect

from app.asr.constants import (
    AUDIO_FRAME_HEADER_FMT,
    AUDIO_FRAME_HEADER_LEN,
    AUDIO_QUEUE_MAXSIZE,
    DROP_WARN_INTERVAL_S,
)
from app.asr.schemas import StreamCloseEvent, StreamOpenEvent
from app.asr.types import StreamState

logger = structlog.get_logger()


class WorkerSession:
    def __init__(self, ws: WebSocket, worker_id: UUID, capacity: int) -> None:
        self.ws = ws
        self.worker_id = worker_id
        self.capacity = max(1, capacity)
        self.streams: dict[UUID, StreamState] = {}
        self.streams_by_idx: dict[int, StreamState] = {}
        self.next_idx: int = 1

    @property
    def load(self) -> int:
        return len(self.streams)

    async def open_stream(
        self,
        meeting_id: UUID,
        stream_id: UUID,
        participant_id: UUID | None,
        display_name: str | None,
        is_local_user: bool,
    ) -> StreamState | None:
        stream_idx = self.next_idx
        self.next_idx += 1
        state = StreamState(
            stream_id=stream_id,
            meeting_id=meeting_id,
            stream_idx=stream_idx,
            participant_id=participant_id,
            audio_queue=asyncio.Queue(maxsize=AUDIO_QUEUE_MAXSIZE),
        )
        self.streams[stream_id] = state
        self.streams_by_idx[stream_idx] = state

        msg = StreamOpenEvent(
            meeting_id=meeting_id,
            stream_id=stream_id,
            stream_idx=stream_idx,
            participant_id=participant_id,
            speaker={"display_name": display_name, "is_local_user": is_local_user},
        )
        try:
            await self.ws.send_text(msg.model_dump_json())
        except (WebSocketDisconnect, RuntimeError) as e:
            logger.warning("failed to send stream_open", stream_id=stream_id, error=str(e))
            await self._teardown_stream(state)
            return None

        state.sender_task = asyncio.create_task(self._sender_loop(state))
        logger.debug(
            "stream assigned to worker",
            stream_id=stream_id,
            worker_id=self.worker_id,
            stream_idx=stream_idx,
        )
        return state

    async def forward_audio_chunk(self, stream_id: UUID, audio_chunk: bytes) -> None:
        state = self.streams.get(stream_id)
        if state is None or state.closed:
            return

        try:
            state.audio_queue.put_nowait(audio_chunk)
        except asyncio.QueueFull:
            try:
                state.audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                state.audio_queue.put_nowait(audio_chunk)
            except asyncio.QueueFull:
                pass

            state.audio_chunks_dropped += 1
            now = time.monotonic()
            if now - state.last_drop_warn_at > DROP_WARN_INTERVAL_S:
                state.last_drop_warn_at = now
                logger.warning(
                    "audio chunks dropped",
                    stream_id=stream_id,
                    total_dropped=state.audio_chunks_dropped,
                )

    async def close_stream(self, stream_id: UUID) -> None:
        state = self.streams.get(stream_id)
        if state is None or state.closed:
            return

        try:
            await self.ws.send_text(StreamCloseEvent(stream_id=stream_id).model_dump_json())
        except (WebSocketDisconnect, RuntimeError) as e:
            logger.debug("failed to send stream_close", stream_id=stream_id, error=str(e))

        await self._teardown_stream(state)
        self.streams.pop(stream_id, None)
        self.streams_by_idx.pop(state.stream_idx, None)

    async def shutdown(self) -> None:
        for state in list(self.streams.values()):
            await self._teardown_stream(state)

    async def _sender_loop(self, state: StreamState) -> None:
        try:
            while True:
                chunk = await state.audio_queue.get()
                if chunk is None or state.closed:
                    return

                state.seq += 1
                frame = self.pack_audio_frame(state.stream_idx, state.seq, chunk)
                try:
                    await self.ws.send_bytes(frame)
                except (WebSocketDisconnect, RuntimeError) as e:
                    logger.debug("failed to send audio chunk", stream_id=state.stream_id, error=str(e))
                    return
        except asyncio.CancelledError:
            return

    @staticmethod
    def pack_audio_frame(stream_idx: int, seq: int, audio_chunk: bytes) -> bytes:
        return struct.pack(AUDIO_FRAME_HEADER_FMT, stream_idx, seq) + audio_chunk

    @staticmethod
    def unpack_audio_frame(frame: bytes) -> tuple[int, int, memoryview]:
        if len(frame) < AUDIO_FRAME_HEADER_LEN:
            raise ValueError(f"audio frame too short: {len(frame)} bytes")

        stream_idx, seq = struct.unpack(AUDIO_FRAME_HEADER_FMT, frame[:AUDIO_FRAME_HEADER_LEN])
        return stream_idx, seq, memoryview(frame)[AUDIO_FRAME_HEADER_LEN:]

    @staticmethod
    async def _teardown_stream(state: StreamState) -> None:
        state.closed = True
        try:
            state.audio_queue.put_nowait(None)
        except asyncio.QueueFull:
            try:
                state.audio_queue.get_nowait()
                state.audio_queue.put_nowait(None)
            except (asyncio.QueueEmpty, asyncio.QueueFull):
                pass

        if state.sender_task is not None:
            try:
                await asyncio.wait_for(state.sender_task, timeout=1.0)
            except (TimeoutError, asyncio.CancelledError):
                state.sender_task.cancel()
