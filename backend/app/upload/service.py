import asyncio
import tempfile
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from uuid import UUID, uuid4

import structlog
from fastapi import UploadFile

from app.asr.clients.final import faster_whisper_client
from app.asr.types import ASRSegment
from app.config import config
from app.ingest.client import minio_client
from app.meeting.client import redis_client
from app.meeting.constants import LifecycleEvent, MeetingStatus
from app.meeting.service import MeetingService
from app.participant.service import ParticipantService
from app.transcript.service import TranscriptService
from app.upload.clients.diarization import diarization_client
from app.upload.clients.ffmpeg import ffmpeg_client
from app.upload.constants import ACCEPTED_EXTENSIONS, CHUNK_BYTES, DEFAULT_SPEAKER_LABEL
from app.upload.exceptions import UploadDurationExceededError, UploadFormatError, UploadTooLargeError
from app.upload.types import DiarSegment

logger = structlog.get_logger()


class UploadService:
    def __init__(
        self,
        meeting_service: MeetingService,
        participant_service: ParticipantService,
        transcript_service: TranscriptService,
    ) -> None:
        self.meeting_service = meeting_service
        self.participant_service = participant_service
        self.transcript_service = transcript_service

    async def create(self, file: UploadFile, title: str | None) -> UUID:
        original_filename = file.filename or "upload"
        ext = self._validate_extension(original_filename)

        meeting = await self.meeting_service.create_for_upload(title=title or original_filename)
        source_key = minio_client.get_upload_source_key(meeting.id, ext)

        tmp_path = await self._spool_to_disk(file)
        try:
            await minio_client.put_file(source_key, str(tmp_path), file.content_type or "application/octet-stream")
        finally:
            tmp_path.unlink(missing_ok=True)

        from app.upload.tasks import process_upload

        await process_upload.kiq(str(meeting.id), source_key)
        logger.info("upload accepted", meeting_id=meeting.id, source_key=source_key, filename=original_filename)
        return meeting.id

    async def process(self, meeting_id: UUID, source_key: str) -> None:
        try:
            await self._process(meeting_id, source_key)
        except Exception:
            logger.exception("upload pipeline failed", meeting_id=meeting_id)
            await self._mark_failed(meeting_id)
            raise

    async def _process(self, meeting_id: UUID, source_key: str) -> None:
        with tempfile.TemporaryDirectory(prefix=f"upload-{meeting_id}-") as workdir:
            workpath = Path(workdir)
            src_path = workpath / "source"
            wav_path = workpath / "normalized.wav"

            await self._publish(meeting_id, MeetingStatus.NORMALIZING, LifecycleEvent.NORMALIZING)
            await minio_client.download_to(source_key, str(src_path))
            await self._validate_duration(str(src_path))
            await ffmpeg_client.normalize_to_wav(str(src_path), str(wav_path))

            await self._publish(meeting_id, MeetingStatus.DIARIZING, LifecycleEvent.DIARIZING)
            diar_segments = await diarization_client.diarize(str(wav_path))
            cluster_count = len({d.cluster_id for d in diar_segments}) or 1
            logger.info("diarization done", meeting_id=meeting_id, clusters=cluster_count)

            await self._publish(meeting_id, MeetingStatus.TRANSCRIBING, LifecycleEvent.TRANSCRIBING)
            segments = await asyncio.to_thread(faster_whisper_client.transcribe, str(wav_path))
            logger.info("transcription done", meeting_id=meeting_id, segments=len(segments))

            grouped = self._align_segments_to_clusters(segments, diar_segments)
            for cluster_id in sorted(grouped):
                stream_id = uuid4()
                label = DEFAULT_SPEAKER_LABEL.format(idx=cluster_id + 1)
                participant = await self.participant_service.create_for_upload(meeting_id, stream_id, label)
                await self.transcript_service.replace_final_for_stream(
                    meeting_id, participant.id, stream_id, grouped[cluster_id]
                )

            await self.meeting_service.set_status(meeting_id, MeetingStatus.FINAL)
            await redis_client.publish_meeting_lifecycle(meeting_id, LifecycleEvent.FINAL)
            await MeetingService.enqueue_graph_build(meeting_id)
            await MeetingService.enqueue_utterance_embeddings(meeting_id)

    async def _validate_duration(self, src_path: str) -> None:
        duration = await ffmpeg_client.probe_duration(src_path)
        if duration > config.upload.MAX_DURATION_SECONDS:
            logger.warning(
                "upload duration exceeds limit",
                duration=duration,
                limit=config.upload.MAX_DURATION_SECONDS,
            )
            raise UploadDurationExceededError()

    async def _publish(self, meeting_id: UUID, status: MeetingStatus, event: LifecycleEvent) -> None:
        await self.meeting_service.set_status(meeting_id, status)
        await redis_client.publish_meeting_lifecycle(meeting_id, event)

    async def _mark_failed(self, meeting_id: UUID) -> None:
        try:
            await self.meeting_service.set_status(meeting_id, MeetingStatus.FAILED)
        except Exception:
            logger.exception("failed to mark meeting as failed", meeting_id=meeting_id)
        await redis_client.publish_meeting_lifecycle(meeting_id, LifecycleEvent.FAILED)

    @staticmethod
    def _validate_extension(filename: str) -> str:
        ext = Path(filename).suffix.lstrip(".").lower()
        if not ext or ext not in ACCEPTED_EXTENSIONS:
            raise UploadFormatError()
        return ext

    @staticmethod
    async def _spool_to_disk(file: UploadFile) -> Path:
        with tempfile.NamedTemporaryFile(prefix="tryniq-upload-", suffix=".bin", delete=False) as out:
            path = Path(out.name)
            size = 0
            try:
                while True:
                    chunk = await file.read(CHUNK_BYTES)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > config.upload.MAX_BYTES:
                        raise UploadTooLargeError()
                    out.write(chunk)
            except Exception:
                path.unlink(missing_ok=True)
                raise

        return path

    @staticmethod
    def _align_segments_to_clusters(
        segments: Iterable[ASRSegment],
        diar_segments: list[DiarSegment],
    ) -> dict[int, list[ASRSegment]]:
        grouped: dict[int, list[ASRSegment]] = defaultdict(list)
        if not diar_segments:
            for seg in segments:
                grouped[0].append(seg)
            return grouped

        for seg in segments:
            grouped[_pick_cluster(seg, diar_segments)].append(seg)
        return grouped


def _pick_cluster(seg: ASRSegment, diar_segments: list[DiarSegment]) -> int:
    best_cluster = diar_segments[0].cluster_id
    best_overlap = 0.0
    for d in diar_segments:
        overlap = min(seg.t_end, d.t_end) - max(seg.t_start, d.t_start)
        if overlap > best_overlap:
            best_overlap = overlap
            best_cluster = d.cluster_id

    if best_overlap > 0:
        return best_cluster

    midpoint = (seg.t_start + seg.t_end) / 2
    nearest = min(
        diar_segments,
        key=lambda d: min(abs(midpoint - d.t_start), abs(midpoint - d.t_end)),
    )
    return nearest.cluster_id
