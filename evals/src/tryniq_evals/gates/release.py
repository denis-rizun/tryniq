from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from langfuse.experiment import ExperimentResult, RegressionError

from tryniq_evals.contracts import GateDirection, MetricGate
from tryniq_evals.gates.models import GateException, GateFailure, SuiteGatePolicy


def fetch_baseline_scores(
    client: Any,
    *,
    dataset_name: str,
    baseline_run_id: str,
) -> dict[str, float]:
    page = 1
    found = False
    while True:
        listing = client.get_dataset_runs(dataset_name=dataset_name, page=page, limit=100)
        if any(run.id == baseline_run_id for run in listing.data):
            found = True
            break
        total_pages = getattr(getattr(listing, "meta", None), "total_pages", 1)
        if page >= total_pages:
            break
        page += 1
    if not found:
        raise ValueError(
            f"approved baseline {baseline_run_id!r} is not a run of {dataset_name!r}"
        )

    scores: dict[str, float] = {}
    page = 1
    while True:
        response = client.api.scores.get_many(
            dataset_run_id=baseline_run_id,
            page=page,
            limit=100,
        )
        for score in response.data:
            if isinstance(score.value, bool) or not isinstance(score.value, (int, float)):
                continue
            value = float(score.value)
            scores[score.name] = value
            if score.name.endswith(".macro"):
                scores[score.name.removesuffix(".macro")] = value
        if page >= response.meta.total_pages:
            break
        page += 1
    return scores


def _run_values(result: ExperimentResult) -> dict[str, float]:
    return {
        evaluation.name: float(evaluation.value)
        for evaluation in result.run_evaluations
        if isinstance(evaluation.value, (int, float)) and not isinstance(evaluation.value, bool)
    }


def _absolute_failure(gate: MetricGate, value: float) -> bool:
    if gate.direction == GateDirection.MIN:
        return value < gate.threshold
    if gate.direction == GateDirection.MAX:
        return value > gate.threshold
    return value != gate.threshold


def _ci_crosses_gate(gate: MetricGate, values: Mapping[str, float]) -> bool:
    low = values.get(f"{gate.metric}.ci95.low")
    high = values.get(f"{gate.metric}.ci95.high")
    if low is None or high is None:
        return gate.primary
    if gate.direction == GateDirection.MIN:
        return low < gate.threshold <= high
    if gate.direction == GateDirection.MAX:
        return low <= gate.threshold < high
    return low <= gate.threshold <= high and (low != high)


def evaluate_release_gates(
    result: ExperimentResult,
    policy: SuiteGatePolicy,
    *,
    baseline_scores: Mapping[str, float] | None,
) -> list[GateFailure]:
    values = _run_values(result)
    failures: list[GateFailure] = []
    for gate in policy.gates:
        metric_name = f"{gate.metric}.macro"
        value = values.get(metric_name, values.get(gate.metric))
        if value is None:
            failures.append(
                GateFailure(
                    metric=gate.metric,
                    value=None,
                    threshold=gate.threshold,
                    reason="required gate metric is missing",
                    direction=gate.direction,
                )
            )
            continue
        if _absolute_failure(gate, value):
            failures.append(
                GateFailure(
                    metric=gate.metric,
                    value=value,
                    threshold=gate.threshold,
                    reason="absolute threshold failed",
                    direction=gate.direction,
                )
            )
        elif gate.primary and _ci_crosses_gate(gate, values):
            failures.append(
                GateFailure(
                    metric=gate.metric,
                    value=value,
                    threshold=gate.threshold,
                    reason="confidence interval crosses gate boundary; run is inconclusive",
                    direction=gate.direction,
                )
            )

        if baseline_scores is None or gate.metric not in baseline_scores:
            continue
        baseline = baseline_scores[gate.metric]
        relative_limit = gate.relative_regression_limit
        if relative_limit is None:
            relative_limit = policy.quality_regression_limit
        if baseline == 0:
            continue
        regression = (
            (baseline - value) / abs(baseline)
            if gate.direction == GateDirection.MIN
            else (value - baseline) / abs(baseline)
        )
        if regression > relative_limit:
            failures.append(
                GateFailure(
                    metric=gate.metric,
                    value=value,
                    threshold=baseline,
                    reason=f"relative regression {regression:.2%} exceeds {relative_limit:.2%}",
                    direction=gate.direction,
                )
            )
        relative_boundary = (
            baseline * (1.0 - relative_limit)
            if gate.direction == GateDirection.MIN
            else baseline * (1.0 + relative_limit)
        )
        low = values.get(f"{gate.metric}.ci95.low")
        high = values.get(f"{gate.metric}.ci95.high")
        crosses_relative_boundary = (
            low is not None
            and high is not None
            and low <= relative_boundary <= high
        )
        if gate.primary and crosses_relative_boundary:
            failures.append(
                GateFailure(
                    metric=gate.metric,
                    value=value,
                    threshold=relative_boundary,
                    reason=(
                        "confidence interval crosses relative regression boundary; "
                        "run is inconclusive"
                    ),
                    direction=gate.direction,
                )
            )
    if not policy.baseline_run_id:
        failures.append(
            GateFailure(
                metric="baseline_run_id",
                value=None,
                threshold=None,
                reason="no approved Langfuse baseline run is pinned",
            )
        )
    return failures


def apply_release_gates(
    result: ExperimentResult,
    policy: SuiteGatePolicy,
    *,
    baseline_scores: Mapping[str, float] | None = None,
    exceptions: tuple[GateException, ...] = (),
    today: date | None = None,
) -> None:
    day = today or date.today()
    active = {
        exception.metric
        for exception in exceptions
        if exception.suite == policy.suite and exception.active_on(day)
    }
    failures = [
        failure
        for failure in evaluate_release_gates(
            result,
            policy,
            baseline_scores=baseline_scores,
        )
        if failure.metric not in active
    ]
    if not failures:
        return
    first = failures[0]
    details = "; ".join(f"{failure.metric}: {failure.reason}" for failure in failures)
    raise RegressionError(
        result=result,
        metric=first.metric,
        value=first.value,
        threshold=first.threshold,
        message=f"Release qualification failed: {details}",
    )
