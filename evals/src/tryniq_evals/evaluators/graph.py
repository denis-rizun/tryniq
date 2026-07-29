from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import Any

import numpy as np
from langfuse.experiment import Evaluation
from scipy.optimize import linear_sum_assignment

from tryniq_evals.contracts import OutcomeStatus, TaskOutcome


def normalize_node_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    return re.sub(r"\s+", " ", normalized)


def maximum_weight_node_matches(
    expected: list[dict[str, Any]],
    predicted: list[dict[str, Any]],
    *,
    threshold: float,
) -> list[tuple[int, int, float]]:
    if not expected or not predicted:
        return []
    weights = np.zeros((len(expected), len(predicted)), dtype=float)
    for row, gold in enumerate(expected):
        for column, candidate in enumerate(predicted):
            if str(gold.get("type")) != str(candidate.get("type")):
                continue
            if normalize_node_text(_node_text(gold)) == normalize_node_text(_node_text(candidate)):
                weights[row, column] = 1.0
                continue
            gold_embedding = gold.get("embedding")
            predicted_embedding = candidate.get("embedding")
            if gold_embedding is not None and predicted_embedding is not None:
                weights[row, column] = _cosine(gold_embedding, predicted_embedding)
    rows, columns = linear_sum_assignment(weights, maximize=True)
    return [
        (int(row), int(column), float(weights[row, column]))
        for row, column in zip(rows, columns, strict=True)
        if weights[row, column] >= threshold
    ]


def graph_scores(
    *,
    input: Any,
    output: Any,
    expected_output: Any = None,
    metadata: dict[str, Any] | None = None,
    **_: Any,
) -> list[Evaluation]:
    del input
    outcome = TaskOutcome[Any].model_validate(output)
    if outcome.status == OutcomeStatus.SKIPPED:
        return []
    if outcome.status == OutcomeStatus.FAILED:
        return [
            Evaluation(
                name=name,
                value=0.0,
                comment=f"Zeroed because graph task failed: {outcome.failure.category}",
                metadata={"gated": True},
            )
            for name in ("schema_validity", "grounding_validity", "node_macro_f1")
        ]

    expected_nodes = list((expected_output or {}).get("nodes", []))
    predicted_nodes = list((outcome.payload or {}).get("nodes", []))
    threshold = float((metadata or {}).get("node_match_threshold", 0.85))
    matches = maximum_weight_node_matches(expected_nodes, predicted_nodes, threshold=threshold)
    matched_expected = {row for row, _, _ in matches}
    matched_predicted = {column for _, column, _ in matches}
    by_type_expected: dict[str, set[int]] = defaultdict(set)
    by_type_predicted: dict[str, set[int]] = defaultdict(set)
    for index, node in enumerate(expected_nodes):
        by_type_expected[str(node.get("type"))].add(index)
    for index, node in enumerate(predicted_nodes):
        by_type_predicted[str(node.get("type"))].add(index)

    evaluations = [
        Evaluation(name="schema_validity", value=1.0, metadata={"gated": True}),
        Evaluation(
            name="node_precision",
            value=len(matched_predicted) / len(predicted_nodes)
            if predicted_nodes
            else float(not expected_nodes),
        ),
        Evaluation(
            name="node_recall",
            value=len(matched_expected) / len(expected_nodes)
            if expected_nodes
            else float(not predicted_nodes),
        ),
    ]
    f1_values: list[float] = []
    for node_type in sorted(set(by_type_expected) | set(by_type_predicted)):
        true_positive = sum(
            1
            for row, column, _ in matches
            if row in by_type_expected[node_type] and column in by_type_predicted[node_type]
        )
        precision = (
            true_positive / len(by_type_predicted[node_type])
            if by_type_predicted[node_type]
            else 0.0
        )
        recall = (
            true_positive / len(by_type_expected[node_type]) if by_type_expected[node_type] else 0.0
        )
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        f1_values.append(f1)
        evaluations.extend(
            [
                Evaluation(name=f"{node_type}.precision", value=precision),
                Evaluation(name=f"{node_type}.recall", value=recall),
                Evaluation(name=f"{node_type}.f1", value=f1),
            ]
        )
    evaluations.append(
        Evaluation(
            name="node_macro_f1",
            value=float(np.mean(f1_values)) if f1_values else 1.0,
        )
    )

    valid_ids = {str(node.get("id")) for node in predicted_nodes}
    source_edges = [
        edge
        for edge in (outcome.payload or {}).get("edges", [])
        if str(edge.get("type")) == "SOURCE"
    ]
    grounded = [
        node
        for node in predicted_nodes
        if str(node.get("type")) in {"DECISION", "ACTION_ITEM", "OPEN_QUESTION"}
    ]
    grounded_ids = {
        str(edge.get("from_id")) for edge in source_edges if str(edge.get("to_id")) in valid_ids
    }
    grounding_validity = (
        sum(str(node.get("id")) in grounded_ids for node in grounded) / len(grounded)
        if grounded
        else 1.0
    )
    evaluations.append(
        Evaluation(
            name="grounding_validity",
            value=grounding_validity,
            metadata={"gated": True},
        )
    )
    return evaluations


def _node_text(node: dict[str, Any]) -> str:
    fields = node.get("fields") or {}
    for key in ("text", "title", "summary", "question", "description", "label"):
        if key in fields:
            return str(fields[key])
        if key in node:
            return str(node[key])
    return ""


def _cosine(left: list[float], right: list[float]) -> float:
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denominator) if denominator else 0.0
