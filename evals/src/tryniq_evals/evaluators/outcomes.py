from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langfuse.experiment import Evaluation

from tryniq_evals.contracts import OutcomeStatus, TaskOutcome


def gated_quality_evaluator(
    name: str,
    score: Callable[[Any, Any, Any, dict[str, Any] | None], float | Evaluation | list[Evaluation]],
) -> Callable[..., Evaluation | list[Evaluation]]:
    def evaluator(
        *,
        input: Any,
        output: Any,
        expected_output: Any = None,
        metadata: dict[str, Any] | None = None,
        **_: Any,
    ) -> Evaluation | list[Evaluation]:
        outcome = TaskOutcome[Any].model_validate(output)
        if outcome.status == OutcomeStatus.SKIPPED:
            return []
        if outcome.status == OutcomeStatus.FAILED:
            return Evaluation(
                name=name,
                value=0.0,
                comment=f"Zeroed because task failed: {outcome.failure.category}",
                metadata={"task_status": outcome.status, "gated": True},
            )
        result = score(input, outcome.payload, expected_output, metadata)
        if isinstance(result, (Evaluation, list)):
            return result
        return Evaluation(name=name, value=float(result), metadata={"gated": True})

    evaluator.__name__ = name.replace(".", "_").replace("-", "_")
    return evaluator


def operational_evaluator(
    *,
    input: Any,
    output: Any,
    expected_output: Any = None,
    metadata: dict[str, Any] | None = None,
    **_: Any,
) -> list[Evaluation]:
    del input, expected_output, metadata
    outcome = TaskOutcome[Any].model_validate(output)
    evaluations: list[Evaluation] = [
        Evaluation(
            name="task.completed",
            value=outcome.status == OutcomeStatus.COMPLETED,
            data_type="BOOLEAN",
        ),
        Evaluation(
            name="task.failed",
            value=outcome.status == OutcomeStatus.FAILED,
            data_type="BOOLEAN",
            comment=outcome.failure.message if outcome.failure else None,
            metadata=outcome.failure.model_dump(mode="json") if outcome.failure else None,
        ),
        Evaluation(
            name="task.skipped",
            value=outcome.status == OutcomeStatus.SKIPPED,
            data_type="BOOLEAN",
            comment=outcome.skip.reason if outcome.skip else None,
            metadata=outcome.skip.model_dump(mode="json") if outcome.skip else None,
        ),
    ]
    values = outcome.measurements.model_dump(exclude_none=True)
    for metric in (
        "latency_ms",
        "time_to_first_token_ms",
        "input_tokens",
        "output_tokens",
        "cost_usd",
        "peak_memory_mb",
        "retry_count",
    ):
        if metric in values:
            evaluations.append(
                Evaluation(
                    name=metric,
                    value=values[metric],
                    metadata={"diagnostic": True},
                )
            )
    evaluations.append(
        Evaluation(
            name="fallback_used",
            value=outcome.measurements.fallback_used,
            data_type="BOOLEAN",
        )
    )
    return evaluations
