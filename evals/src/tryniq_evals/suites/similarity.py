from __future__ import annotations

from typing import Any

from langfuse import RunnerContext

from tryniq_evals.contracts import Cadence, SuiteDefinition, capture_task
from tryniq_evals.evaluators.outcomes import operational_evaluator
from tryniq_evals.evaluators.similarity import (
    cosine_similarity,
    similarity_item_scores,
    similarity_run_scores,
)
from tryniq_evals.evaluators.statistics import build_run_evaluator
from tryniq_evals.suites.support import item_input, run_metadata

DEFINITION = SuiteDefinition(
    suite="similarity",
    version="1.0.0",
    dataset_name="tryniq/similarity/1.0.0/test",
    concurrency=8,
    cadence=(Cadence.NIGHTLY, Cadence.RELEASE),
    evaluators=("pair_f1", "roc_auc", "pr_auc"),
    owner="ai-platform",
)


async def task(*, item: Any, **_: Any) -> dict[str, Any]:
    async def invoke() -> dict[str, Any]:
        from app.core.client import get_ai_client

        value = item_input(item)
        vectors = await get_ai_client().embed([value["left"], value["right"]])
        if len(vectors) != 2:
            raise RuntimeError("embedding provider did not return both vectors")
        score = cosine_similarity(vectors[0], vectors[1])
        threshold = float(value["threshold"])
        return {"score": score, "similar": score >= threshold, "threshold": threshold}

    return (await capture_task(invoke)).model_dump(mode="json")


def experiment(context: RunnerContext) -> Any:
    return context.run_experiment(
        name="Tryniq embedding similarity",
        task=task,
        evaluators=[similarity_item_scores, operational_evaluator],
        run_evaluators=[
            similarity_run_scores,
            build_run_evaluator(primary_metrics=frozenset({"pair_accuracy"})),
        ],
        max_concurrency=DEFINITION.concurrency,
        metadata=run_metadata(
            DEFINITION,
            embedding_model_id="production",
            metric_versions={"langfuse": "4.14.0", "scikit-learn": "1.x"},
        ),
    )
