from __future__ import annotations

import asyncio
from typing import Any

from langfuse import RunnerContext

from tryniq_evals.contracts import Cadence, HardwareRequirement, SuiteDefinition, capture_task
from tryniq_evals.evaluators.outcomes import operational_evaluator
from tryniq_evals.evaluators.speech import final_asr_scores
from tryniq_evals.evaluators.statistics import build_run_evaluator
from tryniq_evals.suites.support import item_input, run_metadata

DEFINITION = SuiteDefinition(
    suite="asr-final",
    version="1.0.0",
    dataset_name="tryniq/asr-final/1.0.0/smoke",
    concurrency=2,
    cadence=(Cadence.LOCAL, Cadence.PR, Cadence.NIGHTLY, Cadence.WEEKLY),
    required_hardware=(HardwareRequirement.CPU,),
    evaluators=("wer", "mer", "wil", "word_accuracy"),
    owner="speech",
)


async def task(*, item: Any, **_: Any) -> dict[str, Any]:
    async def invoke() -> dict[str, Any]:
        from app.asr.clients.final import get_faster_whisper_client
        from app.ingest.clients.minio import minio_client

        value = item_input(item)
        uri = str(value["audio_uri"])
        key = uri.split("/", 3)[-1]
        audio = await minio_client.get_object(key)
        segments = await asyncio.to_thread(get_faster_whisper_client().transcribe, audio)
        rows = [
            {"text": segment.text, "t_start": segment.t_start, "t_end": segment.t_end}
            for segment in segments
        ]
        return {"segments": rows, "transcript": " ".join(row["text"] for row in rows)}

    return (await capture_task(invoke)).model_dump(mode="json")


def experiment(context: RunnerContext) -> Any:
    from app.config import config

    return context.run_experiment(
        name="Tryniq final ASR",
        task=task,
        evaluators=[final_asr_scores, operational_evaluator],
        run_evaluators=[
            build_run_evaluator(
                primary_metrics=frozenset({"wer"}),
                slice_keys=("source", "language", "noise", "speaker_count"),
            )
        ],
        max_concurrency=DEFINITION.concurrency,
        metadata=run_metadata(
            DEFINITION,
            model_id="production:faster-whisper",
            metric_versions={
                "langfuse": "4.14.0",
                "jiwer": "4.0.0",
                "normalization": "EnglishTextNormalizer",
            },
            decoding_configuration={
                "language": config.asr.FINAL_LANGUAGE,
                "device": config.asr.FINAL_DEVICE,
                "compute_type": config.asr.FINAL_COMPUTE_TYPE,
                "beam_size": 5,
                "vad_filter": True,
            },
        ),
    )
