from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

import numpy as np
from langfuse.experiment import Evaluation, ExperimentItemResult
from scipy.stats import bootstrap

from tryniq_evals.contracts import OutcomeStatus, TaskOutcome


def _item_metadata(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return item.get("metadata") or {}
    return item.metadata or {}


def _numeric_scores(result: ExperimentItemResult) -> Iterable[tuple[str, float, dict[str, Any]]]:
    for evaluation in result.evaluations:
        value = evaluation.value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        yield evaluation.name, float(value), evaluation.metadata or {}


def _ci95(values: list[float], seed: int) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1 or len(set(values)) == 1:
        return values[0], values[0]
    interval = bootstrap(
        (np.asarray(values, dtype=float),),
        np.mean,
        confidence_level=0.95,
        n_resamples=9_999,
        method="basic",
        random_state=np.random.default_rng(seed),
    ).confidence_interval
    return float(interval.low), float(interval.high)


def build_run_evaluator(
    *,
    primary_metrics: frozenset[str],
    slice_keys: tuple[str, ...] = (),
    seed: int = 17,
) -> Any:
    def aggregate(
        *,
        item_results: list[ExperimentItemResult],
        **_: Any,
    ) -> list[Evaluation]:
        statuses = defaultdict(int)
        score_values: dict[str, list[float]] = defaultdict(list)
        micro: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
        sliced: dict[tuple[str, str, str], list[float]] = defaultdict(list)

        for result in item_results:
            outcome = TaskOutcome[Any].model_validate(result.output)
            statuses[outcome.status] += 1
            item_metadata = _item_metadata(result.item)
            for name, value, score_metadata in _numeric_scores(result):
                score_values[name].append(value)
                numerator = score_metadata.get("numerator")
                denominator = score_metadata.get("denominator")
                if numerator is not None and denominator is not None:
                    micro[name][0] += float(numerator)
                    micro[name][1] += float(denominator)
                for key in slice_keys:
                    slice_value = item_metadata.get(key)
                    if slice_value is not None:
                        sliced[name, key, str(slice_value)].append(value)

        attempted = len(item_results)
        completed = statuses[OutcomeStatus.COMPLETED]
        failed = statuses[OutcomeStatus.FAILED]
        skipped = statuses[OutcomeStatus.SKIPPED]
        evaluations = [
            Evaluation(name="sample_count", value=attempted),
            Evaluation(name="completed_count", value=completed),
            Evaluation(name="failed_count", value=failed),
            Evaluation(name="skipped_count", value=skipped),
            Evaluation(
                name="failure_rate",
                value=failed / attempted if attempted else 1.0,
                metadata={"gated": True},
            ),
        ]
        for name, values in sorted(score_values.items()):
            low, high = _ci95(values, seed)
            array = np.asarray(values, dtype=float)
            evaluations.extend(
                [
                    Evaluation(name=f"{name}.macro", value=float(np.mean(array))),
                    Evaluation(name=f"{name}.p50", value=float(np.percentile(array, 50))),
                    Evaluation(name=f"{name}.p90", value=float(np.percentile(array, 90))),
                    Evaluation(name=f"{name}.p95", value=float(np.percentile(array, 95))),
                ]
            )
            if name in primary_metrics:
                evaluations.extend(
                    [
                        Evaluation(name=f"{name}.ci95.low", value=low),
                        Evaluation(name=f"{name}.ci95.high", value=high),
                    ]
                )
            numerator, denominator = micro[name]
            if denominator:
                evaluations.append(Evaluation(name=f"{name}.micro", value=numerator / denominator))
        for (name, key, value), scores in sorted(sliced.items()):
            evaluations.append(
                Evaluation(
                    name=f"{name}.slice.{key}={value}",
                    value=float(np.mean(np.asarray(scores, dtype=float))),
                    metadata={"sample_count": len(scores)},
                )
            )
        return evaluations

    aggregate.__name__ = "aggregate_run_scores"
    return aggregate
