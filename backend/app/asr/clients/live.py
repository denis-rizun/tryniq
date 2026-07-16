import asyncio
from uuid import UUID

import structlog
from fastapi import WebSocket

from app.asr.clients.worker_session import WorkerSession

logger = structlog.get_logger()


class LiveASRClient:
    def __init__(self) -> None:
        self._workers: list[WorkerSession] = []
        self._stream_index: dict[UUID, WorkerSession] = {}
        self._lock = asyncio.Lock()

    async def register_worker(self, ws: WebSocket, worker_id: UUID, capacity: int) -> WorkerSession:
        worker = WorkerSession(ws, worker_id, capacity)
        async with self._lock:
            self._workers.append(worker)

        logger.debug("worker connected", worker_id=worker_id, capacity=worker.capacity)
        return worker

    async def unregister_worker(self, worker: WorkerSession) -> None:
        async with self._lock:
            if worker in self._workers:
                self._workers.remove(worker)

            stream_ids = list(worker.streams.keys())
            for stream_id in stream_ids:
                self._stream_index.pop(stream_id, None)

        await worker.shutdown()
        logger.debug("worker disconnected", worker_id=worker.worker_id, streams=len(stream_ids))

    async def assign_stream(
        self,
        meeting_id: UUID,
        stream_id: UUID,
        participant_id: UUID | None,
        display_name: str | None,
        is_local_user: bool,
        stream_offset_seconds: float,
    ) -> WorkerSession | None:
        async with self._lock:
            if not self._workers:
                return None

            worker = min(self._workers, key=lambda w: w.load)
            self._stream_index[stream_id] = worker

        state = await worker.open_stream(
            meeting_id, stream_id, participant_id, display_name, is_local_user, stream_offset_seconds
        )
        if state is None:
            async with self._lock:
                self._stream_index.pop(stream_id, None)

            return None
        return worker

    async def forward_audio_chunk(self, stream_id: UUID, audio_chunk: bytes) -> None:
        worker = self._stream_index.get(stream_id)
        if worker is None:
            return

        await worker.forward_audio_chunk(stream_id, audio_chunk)

    async def close_stream(self, stream_id: UUID) -> None:
        worker = self._stream_index.get(stream_id)
        if worker is None:
            return

        await worker.close_stream(stream_id)
        async with self._lock:
            self._stream_index.pop(stream_id, None)
