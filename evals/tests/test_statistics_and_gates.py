from datetime import date
from types import SimpleNamespace

import pytest
from langfuse.experiment import (
    Evaluation,
    ExperimentItemResult,
    ExperimentResult,
    RegressionError,
)

from tryniq_evals.contracts import GateDirection, MetricGate, TaskOutcome
from tryniq_evals.evaluators.statistics import build_run_evaluator
from tryniq_evals.gates.models import GateException, SuiteGatePolicy
from tryniq_evals.gates.release import apply_release_gates, fetch_baseline_scores


def item_result(score: float, status: TaskOutcome = None) -> ExperimentItemResult:
    outcome = status or TaskOutcome.completed({"ok": True})
    return ExperimentItemResult(
        item={"input": {}, "expected_output": {}, "metadata": {"source": "synthetic"}},
        output=outcome.model_dump(mode="json"),
        evaluations=[Evaluation(name="quality", value=score)],
        trace_id="trace",
        dataset_run_id="run",
    )


def experiment_result(evaluations: list[Evaluation]) -> ExperimentResult:
    return ExperimentResult(
        name="suite",
        run_name="run",
        description=None,
        item_results=[],
        run_evaluations=evaluations,
        experiment_id="experiment",
        dataset_run_id="run",
        dataset_run_url="http://langfuse/run",
    )


def test_run_statistics_publish_counts_percentiles_ci_and_slices() -> None:
    evaluator = build_run_evaluator(
        primary_metrics=frozenset({"quality"}),
        slice_keys=("source",),
        seed=7,
    )
    results = evaluator(item_results=[item_result(0.7), item_result(0.9)])
    scores = {result.name: result.value for result in results}
    assert scores["sample_count"] == 2
    assert scores["quality.macro"] == pytest.approx(0.8)
    assert scores["quality.p50"] == pytest.approx(0.8)
    assert scores["quality.ci95.low"] <= 0.8 <= scores["quality.ci95.high"]
    assert scores["quality.slice.source=synthetic"] == pytest.approx(0.8)


def test_release_gate_raises_regression_error_for_inconclusive_ci() -> None:
    result = experiment_result(
        [
            Evaluation(name="quality.macro", value=0.85),
            Evaluation(name="quality.ci95.low", value=0.75),
            Evaluation(name="quality.ci95.high", value=0.95),
        ]
    )
    policy = SuiteGatePolicy(
        suite="test",
        baseline_run_id="baseline",
        gates=(
            MetricGate(
                metric="quality",
                direction=GateDirection.MIN,
                threshold=0.8,
                primary=True,
            ),
        ),
    )
    with pytest.raises(RegressionError, match="inconclusive"):
        apply_release_gates(result, policy)


def test_active_expiring_exception_is_narrow() -> None:
    result = experiment_result([Evaluation(name="quality.macro", value=0.5)])
    policy = SuiteGatePolicy(
        suite="test",
        baseline_run_id="baseline",
        gates=(MetricGate(metric="quality", direction=GateDirection.MIN, threshold=0.8),),
    )
    exception = GateException(
        suite="test",
        metric="quality",
        owner="owner",
        reason="known issue",
        langfuse_run_url="http://langfuse/run",
        failing_slices=("long",),
        expires=date(2026, 8, 1),
    )
    apply_release_gates(
        result,
        policy,
        exceptions=(exception,),
        today=date(2026, 7, 29),
    )
    with pytest.raises(RegressionError):
        apply_release_gates(
            result,
            policy,
            exceptions=(exception,),
            today=date(2026, 8, 2),
        )


def test_baseline_scores_are_loaded_from_the_pinned_dataset_run() -> None:
    scores_api = SimpleNamespace(
        get_many=lambda **_: SimpleNamespace(
            data=[
                SimpleNamespace(name="quality.macro", value=0.9),
                SimpleNamespace(name="quality.ci95.low", value=0.8),
            ],
            meta=SimpleNamespace(total_pages=1),
        )
    )
    client = SimpleNamespace(
        get_dataset_runs=lambda **_: SimpleNamespace(
            data=[SimpleNamespace(id="approved-run")]
        ),
        api=SimpleNamespace(scores=scores_api),
    )

    scores = fetch_baseline_scores(
        client,
        dataset_name="tryniq/test/1.0.0/test",
        baseline_run_id="approved-run",
    )

    assert scores["quality"] == 0.9
    assert scores["quality.ci95.low"] == 0.8
