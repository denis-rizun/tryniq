from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from langfuse import RunnerContext

from tryniq_evals.contracts import Cadence, HardwareRequirement, SuiteDefinition, capture_task
from tryniq_evals.evaluators.outcomes import operational_evaluator
from tryniq_evals.evaluators.speech import diarization_scores
from tryniq_evals.evaluators.statistics import build_run_evaluator
from tryniq_evals.suites.support import item_input, run_metadata

DEFINITION = SuiteDefinition(
    suite="diarization",
    version="1.0.0",
    dataset_name="tryniq/diarization/1.0.0/smoke",
    concurrency=1,
    cadence=(Cadence.LOCAL, Cadence.NIGHTLY, Cadence.WEEKLY),
    required_hardware=(HardwareRequirement.CPU,),
    evaluators=("der", "jer", "speaker_count_accuracy"),
    owner="speech",
)


async def task(*, item: Any, **_: Any) -> dict[str, Any]:
    async def invoke() -> dict[str, Any]:
        from app.ingest.clients.minio import minio_client
        from app.upload.clients.diarization import get_diarization_client

        value = item_input(item)
        key = str(value["audio_uri"]).split("/", 3)[-1]
        audio = await minio_client.get_object(key)
        with tempfile.NamedTemporaryFile(suffix=".wav") as target:
            Path(target.name).write_bytes(audio)
            result = await get_diarization_client().diarize_with_status(target.name)
        return {
            "segments": [
                {
                    "t_start": segment.t_start,
                    "t_end": segment.t_end,
                    "speaker": str(segment.cluster_id),
                }
                for segment in result.segments
            ],
            "fallback_used": result.fallback_used,
            "failure": result.failure,
        }

    return (await capture_task(invoke)).model_dump(mode="json")


def experiment(context: RunnerContext) -> Any:
    return context.run_experiment(
        name="Tryniq upload diarization",
        task=task,
        evaluators=[diarization_scores, operational_evaluator],
        run_evaluators=[
            build_run_evaluator(
                primary_metrics=frozenset({"der", "jer"}),
                slice_keys=("source", "overlap", "speaker_count", "noise"),
            )
        ],
        max_concurrency=DEFINITION.concurrency,
        metadata=run_metadata(
            DEFINITION,
            model_id="production:diarizen",
            metric_versions={"langfuse": "4.14.0", "pyannote.metrics": "4.1"},
        ),
    )
