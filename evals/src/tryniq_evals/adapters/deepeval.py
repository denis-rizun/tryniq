from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from langfuse.experiment import Evaluation

from tryniq_evals.contracts import OutcomeStatus, TaskOutcome


class DeepEvalMetric(Protocol):
    score: float | None
    reason: str | None
    success: bool | None

    async def a_measure(self, test_case: Any) -> float: ...


MetricFactory = Callable[[], DeepEvalMetric]
TestCaseFactory = Callable[[Any, Any, Any, dict[str, Any] | None], Any]


def build_deepeval_evaluator(
    *,
    name: str,
    metric_factory: MetricFactory,
    test_case_factory: TestCaseFactory,
    rubric_version: str,
    gated: bool = False,
) -> Callable[..., Any]:
    """Create an isolated per-item DeepEval evaluator for Langfuse.

    A new metric instance is constructed for every item. This deliberately avoids
    DeepEval's runner, tracing, login, and result storage.
    """

    async def evaluator(
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
            category = outcome.failure.category if outcome.failure else "unknown"
            return Evaluation(
                name=name,
                value=0.0,
                comment=f"Task failed before semantic scoring: {category}",
                metadata={
                    "rubric_version": rubric_version,
                    "gated": gated,
                    "task_status": outcome.status,
                },
            )

        metric = metric_factory()
        test_case = test_case_factory(input, outcome.payload, expected_output, metadata)
        await metric.a_measure(test_case)
        score = metric.score
        if score is None:
            raise ValueError(f"DeepEval metric {name!r} returned no score")
        reason = metric.reason or "DeepEval metric did not provide a reason"
        success = bool(metric.success)
        return Evaluation(
            name=name,
            value=float(score),
            comment=reason,
            metadata={
                "rubric_version": rubric_version,
                "success": success,
                "gated": gated,
                "engine": "deepeval",
            },
        )

    evaluator.__name__ = f"deepeval_{name.replace('.', '_').replace('-', '_')}"
    return evaluator
