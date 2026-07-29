from __future__ import annotations

from typing import Any

from deepeval.metrics import ExactMatchMetric
from deepeval.test_case import LLMTestCase
from langfuse import RunnerContext

from tryniq_evals.adapters.deepeval import build_deepeval_evaluator
from tryniq_evals.contracts import Cadence, SuiteDefinition, TaskOutcome
from tryniq_evals.evaluators.outcomes import operational_evaluator
from tryniq_evals.evaluators.statistics import build_run_evaluator
from tryniq_evals.suites.support import item_input, run_metadata

DEFINITION = SuiteDefinition(
    suite="synthetic-foundation",
    version="1.0.0",
    dataset_name="tryniq/synthetic-foundation/1.0.0/smoke",
    concurrency=4,
    cadence=(Cadence.LOCAL, Cadence.PR),
    evaluators=("exact_match",),
    owner="ai-platform",
)


async def task(*, item: Any, **_: Any) -> dict[str, Any]:
    payload = item_input(item)
    actual = payload["actual_output"] if isinstance(payload, dict) else payload
    return TaskOutcome.completed(str(actual)).model_dump(mode="json")


def _test_case(
    input: Any,
    actual: Any,
    expected: Any,
    metadata: dict[str, Any] | None,
) -> LLMTestCase:
    del metadata
    raw_input = input.get("prompt", input) if isinstance(input, dict) else input
    expected_text = (
        expected.get("expected_output", expected) if isinstance(expected, dict) else expected
    )
    return LLMTestCase(
        input=str(raw_input),
        actual_output=str(actual),
        expected_output=str(expected_text),
    )


exact_match = build_deepeval_evaluator(
    name="exact_match",
    metric_factory=ExactMatchMetric,
    test_case_factory=_test_case,
    rubric_version="deepeval-exact-match/1",
    gated=True,
)


def experiment(context: RunnerContext) -> Any:
    return context.run_experiment(
        name="Tryniq synthetic foundation",
        description="Dataset-backed SDK compatibility and DeepEval adapter smoke run.",
        task=task,
        evaluators=[exact_match, operational_evaluator],
        run_evaluators=[build_run_evaluator(primary_metrics=frozenset({"exact_match"}), seed=17)],
        max_concurrency=DEFINITION.concurrency,
        metadata=run_metadata(
            DEFINITION,
            metric_versions={"langfuse": "4.14.0", "deepeval": "4.1.4"},
        ),
    )
