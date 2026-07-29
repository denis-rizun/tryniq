from __future__ import annotations

from typing import Any

import numpy as np
from langfuse.experiment import Evaluation, ExperimentItemResult
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from tryniq_evals.contracts import OutcomeStatus, TaskOutcome


def similarity_item_scores(
    *,
    input: Any,
    output: Any,
    expected_output: Any = None,
    metadata: dict[str, Any] | None = None,
    **_: Any,
) -> list[Evaluation]:
    del input, metadata
    outcome = TaskOutcome[Any].model_validate(output)
    if outcome.status == OutcomeStatus.SKIPPED:
        return []
    if outcome.status == OutcomeStatus.FAILED:
        return [Evaluation(name="pair_accuracy", value=0.0, metadata={"gated": True})]
    expected = bool((expected_output or {}).get("similar", expected_output))
    predicted = bool(outcome.payload["similar"])
    return [
        Evaluation(name="pair_accuracy", value=float(predicted == expected)),
        Evaluation(name="similarity_score", value=float(outcome.payload["score"])),
    ]


def similarity_run_scores(
    *,
    item_results: list[ExperimentItemResult],
    **_: Any,
) -> list[Evaluation]:
    labels: list[int] = []
    predictions: list[int] = []
    scores: list[float] = []
    for result in item_results:
        outcome = TaskOutcome[Any].model_validate(result.output)
        if outcome.status != OutcomeStatus.COMPLETED:
            continue
        expected = (
            result.item.get("expected_output")
            if isinstance(result.item, dict)
            else result.item.expected_output
        )
        labels.append(int(bool((expected or {}).get("similar", expected))))
        predictions.append(int(bool(outcome.payload["similar"])))
        scores.append(float(outcome.payload["score"]))
    if not labels:
        return []
    tn, fp, fn, tp = confusion_matrix(labels, predictions, labels=[0, 1]).ravel()
    evaluations = [
        Evaluation(name="pair_accuracy", value=float(accuracy_score(labels, predictions))),
        Evaluation(
            name="pair_precision",
            value=float(precision_score(labels, predictions, zero_division=0)),
        ),
        Evaluation(
            name="pair_recall",
            value=float(recall_score(labels, predictions, zero_division=0)),
        ),
        Evaluation(name="pair_f1", value=float(f1_score(labels, predictions, zero_division=0))),
        Evaluation(name="false_positive_rate", value=float(fp / (fp + tn)) if fp + tn else 0.0),
        Evaluation(name="false_negative_rate", value=float(fn / (fn + tp)) if fn + tp else 0.0),
    ]
    if len(set(labels)) == 2:
        evaluations.extend(
            [
                Evaluation(name="roc_auc", value=float(roc_auc_score(labels, scores))),
                Evaluation(name="pr_auc", value=float(average_precision_score(labels, scores))),
            ]
        )
    return evaluations


def cosine_similarity(left: list[float], right: list[float]) -> float:
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denominator) if denominator else 0.0
