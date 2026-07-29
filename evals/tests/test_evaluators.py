from tryniq_evals.contracts import FailureCategory, TaskOutcome
from tryniq_evals.evaluators.citations import citation_scores
from tryniq_evals.evaluators.end_to_end import end_to_end_scores
from tryniq_evals.evaluators.graph import graph_scores, maximum_weight_node_matches
from tryniq_evals.evaluators.retrieval import retrieval_scores
from tryniq_evals.evaluators.speech import diarization_scores, final_asr_scores, live_asr_scores


def values(evaluations):
    return {evaluation.name: evaluation.value for evaluation in evaluations}


def test_final_asr_uses_jiwer_with_locked_normalizer() -> None:
    scores = final_asr_scores(
        input={},
        output=TaskOutcome.completed({"transcript": "Hello world"}).model_dump(mode="json"),
        expected_output={"transcript": "hello brave world"},
    )
    result = values(scores)
    assert result["wer"] == 1 / 3
    assert result["deletion_rate"] == 1 / 3


def test_diarization_uses_standard_metrics_for_perfect_fixture() -> None:
    segments = {
        "segments": [
            {"t_start": 0.0, "t_end": 1.0, "speaker": "a"},
            {"t_start": 1.0, "t_end": 2.0, "speaker": "b"},
        ]
    }
    scores = diarization_scores(
        input={},
        output=TaskOutcome.completed(segments).model_dump(mode="json"),
        expected_output=segments,
    )
    result = values(scores)
    assert result["der"] == 0
    assert result["jer"] == 0
    assert result["speaker_count_accuracy"] == 1


def test_live_asr_uses_captured_protocol_events_for_latency() -> None:
    scores = live_asr_scores(
        input={},
        output=TaskOutcome.completed(
            {
                "transcript": "hello world",
                "partials": ["hello", "hello world"],
                "events": [
                    {
                        "kind": "partial_transcript",
                        "observed_at_ms": 125.0,
                    },
                    {
                        "kind": "transcript_segment",
                        "observed_at_ms": 1_500.0,
                        "t_end": 1.2,
                    },
                ],
            }
        ).model_dump(mode="json"),
        expected_output={"transcript": "hello world"},
    )

    result = values(scores)
    assert result["time_to_first_partial_ms"] == 125.0
    assert result["final_latency_ms"] == 300.0


def test_retrieval_scores_are_calculated_by_ranx() -> None:
    scores = retrieval_scores(
        input={"query": "decision"},
        output=TaskOutcome.completed(
            {
                "results": [
                    {"id": "d1", "score": 2.0},
                    {"id": "d2", "score": 1.0},
                ]
            }
        ).model_dump(mode="json"),
        expected_output={"relevance": {"d1": 2, "d3": 1}},
        metadata={"stable_id": "q1"},
    )
    result = values(scores)
    assert result["precision_at_1"] == 1
    assert result["recall_at_5"] == 0.5
    assert 0 < result["ndcg_at_5"] < 1


def test_graph_matching_is_one_to_one_and_type_aware() -> None:
    expected = [
        {"type": "DECISION", "text": "Ship Friday", "embedding": [1.0, 0.0]},
        {"type": "TOPIC", "text": "Launch", "embedding": [0.0, 1.0]},
    ]
    predicted = [
        {"type": "DECISION", "text": " ship   friday "},
        {"type": "TOPIC", "text": "Release", "embedding": [0.0, 1.0]},
        {"type": "ACTION_ITEM", "text": "Ship Friday", "embedding": [1.0, 0.0]},
    ]
    matches = maximum_weight_node_matches(expected, predicted, threshold=0.85)
    assert {(row, column) for row, column, _ in matches} == {(0, 0), (1, 1)}


def test_failed_graph_task_zeroes_every_gated_quality_metric() -> None:
    scores = graph_scores(
        input={},
        output=TaskOutcome.failed(
            FailureCategory.INVARIANT,
            "invalid operations",
        ).model_dump(mode="json"),
        expected_output={},
    )

    assert values(scores) == {
        "schema_validity": 0.0,
        "grounding_validity": 0.0,
        "node_macro_f1": 0.0,
    }


def test_citation_validity_rejects_non_retrieved_ids() -> None:
    scores = citation_scores(
        input={},
        output=TaskOutcome.completed(
            {
                "retrieved_utterance_ids": ["u1"],
                "citations": [{"utterance_id": "u1"}, {"utterance_id": "u2"}],
            }
        ).model_dump(mode="json"),
        expected_output={"citation_utterance_ids": ["u1"]},
    )
    assert values(scores)["citation_id_validity"] == 0.5


def test_end_to_end_requires_final_and_idempotent_durable_state() -> None:
    scores = end_to_end_scores(
        output=TaskOutcome.completed(
            {"status": "final", "idempotent": True}
        ).model_dump(mode="json")
    )
    assert values(scores) == {"completion": 1.0, "idempotency": 1.0}
