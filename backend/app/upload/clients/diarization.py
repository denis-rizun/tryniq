import asyncio
from threading import Lock
from typing import Any

import structlog

from app.config import config
from app.upload.clients.ffmpeg import ffmpeg_client
from app.upload.types import DiarSegment

logger = structlog.get_logger()


class DiarizationClient:
    def __init__(self) -> None:
        self._pipeline: Any | None = None
        self._lock = Lock()

    async def diarize(self, wav_path: str) -> list[DiarSegment]:
        try:
            return await asyncio.to_thread(self._run, wav_path)
        except (ImportError, RuntimeError):
            logger.warning("diarizen unavailable, using single cluster")
            return await self._run_fallback(wav_path)

    def _run(self, wav_path: str) -> list[DiarSegment]:
        pipeline = self._ensure_pipeline()
        annotation = pipeline(wav_path)

        out: list[DiarSegment] = []
        label_to_idx: dict[str, int] = {}
        for segment, _track, label in annotation.itertracks(yield_label=True):
            key = str(label)
            if key not in label_to_idx:
                label_to_idx[key] = len(label_to_idx)

            out.append(
                DiarSegment(
                    t_start=float(segment.start),
                    t_end=float(segment.end),
                    cluster_id=label_to_idx[key],
                )
            )
        return out

    def _ensure_pipeline(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline

        with self._lock:
            if self._pipeline is not None:
                return self._pipeline

            _allow_unsafe_torch_load()
            from diarizen.pipelines.inference import DiariZenPipeline  # type: ignore[import-not-found]

            logger.info("loading diarizen pipeline", model=config.upload.DIARIZEN_MODEL)
            self._pipeline = DiariZenPipeline.from_pretrained(config.upload.DIARIZEN_MODEL)
        return self._pipeline

    @staticmethod
    async def _run_fallback(wav_path: str) -> list[DiarSegment]:
        duration = await ffmpeg_client.probe_duration(wav_path)
        return [DiarSegment(t_start=0.0, t_end=duration, cluster_id=0)]


_torch_load_patched = False


def _allow_unsafe_torch_load() -> None:
    global _torch_load_patched
    if _torch_load_patched:
        return

    import torch

    original = torch.load

    def patched(*args: Any, **kwargs: Any) -> Any:
        if kwargs.get("weights_only") in (None, True):
            kwargs["weights_only"] = False
        return original(*args, **kwargs)

    torch.load = patched  # type: ignore[assignment]
    _torch_load_patched = True


diarization_client = DiarizationClient()
