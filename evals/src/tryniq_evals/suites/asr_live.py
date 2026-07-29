from __future__ import annotations

import asyncio
import io
import json
import os
import wave
from contextlib import suppress
from time import perf_counter
from typing import Any
from uuid import UUID

import websockets
from langfuse import RunnerContext
from sqlmodel import select

from tryniq_evals.contracts import (
    Cadence,
    HardwareRequirement,
    SuiteDefinition,
    capture_task,
)
from tryniq_evals.evaluators.outcomes import operational_evaluator
from tryniq_evals.evaluators.speech import live_asr_scores
from tryniq_evals.evaluators.statistics import build_run_evaluator
from tryniq_evals.suites.support import item_input, run_metadata


class DependencyUnavailableError(RuntimeError):
    pass


DEFINITION = SuiteDefinition(
    suite="asr-live",
    version="1.0.0",
    dataset_name="tryniq/asr-live/1.0.0/smoke",
    concurrency=2,
    cadence=(Cadence.LOCAL, Cadence.NIGHTLY, Cadence.WEEKLY),
    required_hardware=(HardwareRequirement.APPLE_SILICON, HardwareRequirement.STREAMER),
    evaluators=(
        "wer",
        "revision_rate",
        "stability",
        "finalization_accuracy",
        "time_to_first_partial_ms",
        "final_latency_ms",
    ),
    owner="speech",
)


async def task(*, item: Any, **_: Any) -> dict[str, Any]:
    async def invoke() -> dict[str, Any]:
        from app.db import async_session
        from app.ingest.clients.minio import minio_client
        from app.meeting.client import redis_client
        from app.meeting.constants import EVENT_CHANNEL
        from app.transcript.models import Utterance

        value = item_input(item)
        meeting_id = UUID(value["meeting_id"])
        stream_id = UUID(value["stream_id"])
        audio_key = str(value["audio_uri"]).split("/", 3)[-1]
        pcm, duration = _pcm(await minio_client.get_object(audio_key))
        events: list[dict[str, Any]] = []
        stream_started = perf_counter()

        async def collect_events() -> None:
            channel = EVENT_CHANNEL.format(meeting_id=meeting_id)
            async for raw in redis_client.subscribe(channel, idle_timeout_s=1.0):
                if raw is None:
                    continue
                event = json.loads(raw)
                if event.get("stream_id") == str(stream_id):
                    event["observed_at_ms"] = (perf_counter() - stream_started) * 1000
                    events.append(event)

        collector = asyncio.create_task(collect_events())
        backend = os.environ.get("EVAL_BACKEND_WS_URL")
        if not backend:
            raise DependencyUnavailableError("EVAL_BACKEND_WS_URL is required")
        uri = f"{backend.rstrip('/')}/api/v1/meetings/{meeting_id}/streams/{stream_id}"
        try:
            async with websockets.connect(uri) as socket:
                await socket.send(
                    json.dumps(
                        {
                            "kind": "init",
                            "meeting_id": str(meeting_id),
                            "stream_id": str(stream_id),
                            "speaker": {
                                "display_name": "Evaluation Speaker",
                                "is_local_user": True,
                            },
                            "audio_format": {
                                "sample_rate": 16000,
                                "encoding": "pcm_s16le",
                                "channels": 1,
                            },
                            "client_version": "tryniq-evals/1.0.0",
                        }
                    )
                )
                frame_bytes = 640
                for offset in range(0, len(pcm), frame_bytes):
                    await socket.send(pcm[offset : offset + frame_bytes])
                    await asyncio.sleep(0.02)
                await socket.send(json.dumps({"kind": "stream_end"}))
            await asyncio.sleep(min(2.0, max(0.5, duration * 0.1)))
        finally:
            collector.cancel()
            with suppress(asyncio.CancelledError):
                await collector

        async with async_session() as session:
            utterances = list(
                (
                    await session.exec(
                        select(Utterance)
                        .where(Utterance.stream_id == stream_id)
                        .order_by(Utterance.t_start)
                    )
                ).all()
            )
        partials = [
            str(event["text"])
            for event in events
            if event.get("kind") == "partial_transcript" and event.get("text")
        ]
        transcript = " ".join(utterance.text for utterance in utterances if utterance.text)
        if not transcript:
            raise DependencyUnavailableError(
                "Swift streamer produced no transcript; verify worker connection and model license"
            )
        return {
            "transcript": transcript,
            "partials": partials,
            "events": events,
            "audio_duration_s": duration,
        }

    return (await capture_task(invoke)).model_dump(mode="json")


def _pcm(wav_bytes: bytes) -> tuple[bytes, float]:
    with wave.open(io.BytesIO(wav_bytes), "rb") as source:
        if (
            source.getframerate() != 16_000
            or source.getnchannels() != 1
            or source.getsampwidth() != 2
        ):
            raise ValueError("live ASR fixture must be 16 kHz mono PCM16 WAV")
        frames = source.readframes(source.getnframes())
        return frames, source.getnframes() / source.getframerate()


def experiment(context: RunnerContext) -> Any:
    return context.run_experiment(
        name="Tryniq live ASR",
        task=task,
        evaluators=[live_asr_scores, operational_evaluator],
        run_evaluators=[
            build_run_evaluator(
                primary_metrics=frozenset({"wer", "stability"}),
                slice_keys=("source", "noise", "speaker_count"),
            )
        ],
        max_concurrency=DEFINITION.concurrency,
        metadata=run_metadata(
            DEFINITION,
            model_id="production:parakeet-fluid-audio",
            metric_versions={
                "langfuse": "4.14.0",
                "jiwer": "4.0.0",
                "normalization": "EnglishTextNormalizer",
            },
            decoding_configuration={
                "sample_rate": 16_000,
                "encoding": "pcm_s16le",
                "channels": 1,
                "pace": "real-time",
                "wire_contract": "production-websocket",
            },
        ),
    )
