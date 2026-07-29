from __future__ import annotations

from collections import defaultdict
from typing import Any

from langfuse.experiment import Evaluation

from tryniq_evals.contracts import OutcomeStatus, TaskOutcome


def _failed_speech_scores(
    outcome: TaskOutcome[Any],
    values: dict[str, float],
) -> list[Evaluation]:
    if outcome.status == OutcomeStatus.SKIPPED:
        return []
    if outcome.status == OutcomeStatus.FAILED:
        return [
            Evaluation(
                name=name,
                value=value,
                comment=f"Worst-case score because task failed: {outcome.failure.category}",
                metadata={"gated": True},
            )
            for name, value in values.items()
        ]
    return []


def final_asr_scores(
    *,
    input: Any,
    output: Any,
    expected_output: Any = None,
    metadata: dict[str, Any] | None = None,
    **_: Any,
) -> list[Evaluation]:
    del input, metadata
    outcome = TaskOutcome[Any].model_validate(output)
    if outcome.status != OutcomeStatus.COMPLETED:
        return _failed_speech_scores(
            outcome,
            {
                "wer": 1.0,
                "mer": 1.0,
                "wil": 1.0,
                "word_accuracy": 0.0,
            },
        )

    from jiwer import process_words
    from whisper_normalizer.english import EnglishTextNormalizer

    normalizer = EnglishTextNormalizer()
    reference = normalizer(_transcript_text(expected_output))
    hypothesis = normalizer(_transcript_text(outcome.payload))
    measures = process_words(reference, hypothesis)
    reference_words = measures.hits + measures.substitutions + measures.deletions
    denominator = max(reference_words, 1)
    values = {
        "wer": measures.wer,
        "mer": measures.mer,
        "wil": measures.wil,
        "word_accuracy": max(0.0, 1.0 - measures.wer),
        "substitution_rate": measures.substitutions / denominator,
        "deletion_rate": measures.deletions / denominator,
        "insertion_rate": measures.insertions / denominator,
    }
    common = {
        "reference_words": reference_words,
        "hits": measures.hits,
        "substitutions": measures.substitutions,
        "deletions": measures.deletions,
        "insertions": measures.insertions,
        "normalization": "whisper-normalizer.EnglishTextNormalizer",
        "engine": "jiwer",
    }
    return [
        Evaluation(
            name=name,
            value=float(value),
            metadata={
                **common,
                "gated": True,
                **(
                    {
                        "numerator": measures.substitutions
                        + measures.deletions
                        + measures.insertions,
                        "denominator": reference_words,
                    }
                    if name == "wer"
                    else {}
                ),
            },
        )
        for name, value in values.items()
    ]


def live_asr_scores(
    *,
    input: Any,
    output: Any,
    expected_output: Any = None,
    metadata: dict[str, Any] | None = None,
    **kwargs: Any,
) -> list[Evaluation]:
    evaluations = final_asr_scores(
        input=input,
        output=output,
        expected_output=expected_output,
        metadata=metadata,
        **kwargs,
    )
    outcome = TaskOutcome[Any].model_validate(output)
    if outcome.status != OutcomeStatus.COMPLETED:
        return evaluations
    partials = [str(value) for value in (outcome.payload or {}).get("partials", []) if value]
    if not partials:
        evaluations.extend(
            [
                Evaluation(name="revision_rate", value=0.0),
                Evaluation(name="stability", value=0.0),
                Evaluation(name="finalization_accuracy", value=0.0),
            ]
        )
    else:
        revisions = 0
        stable = 0
        possible = 0
        for previous, current in zip(partials, partials[1:], strict=False):
            previous_tokens = previous.split()
            current_tokens = current.split()
            prefix = 0
            for left, right in zip(previous_tokens, current_tokens, strict=False):
                if left != right:
                    break
                prefix += 1
            revisions += max(len(previous_tokens), len(current_tokens)) - prefix
            stable += prefix
            possible += max(len(previous_tokens), len(current_tokens))
        final_text = _transcript_text(outcome.payload)
        evaluations.extend(
            [
                Evaluation(
                    name="revision_rate",
                    value=revisions / possible if possible else 0.0,
                ),
                Evaluation(
                    name="stability",
                    value=stable / possible if possible else 1.0,
                ),
                Evaluation(
                    name="finalization_accuracy",
                    value=float(partials[-1].strip() == final_text.strip()),
                ),
            ]
        )

    events = list((outcome.payload or {}).get("events", []))
    partial_observations = [
        float(event["observed_at_ms"])
        for event in events
        if event.get("kind") == "partial_transcript" and event.get("observed_at_ms") is not None
    ]
    if partial_observations:
        evaluations.append(
            Evaluation(
                name="time_to_first_partial_ms",
                value=min(partial_observations),
                metadata={"engine": "captured-production-protocol"},
            )
        )
    final_latencies = [
        max(0.0, float(event["observed_at_ms"]) - float(event["t_end"]) * 1000)
        for event in events
        if event.get("kind") == "transcript_segment"
        and event.get("observed_at_ms") is not None
        and event.get("t_end") is not None
    ]
    if final_latencies:
        evaluations.append(
            Evaluation(
                name="final_latency_ms",
                value=float(max(final_latencies)),
                metadata={
                    "engine": "captured-production-protocol",
                    "segment_count": len(final_latencies),
                },
            )
        )
    return evaluations


def diarization_scores(
    *,
    input: Any,
    output: Any,
    expected_output: Any = None,
    metadata: dict[str, Any] | None = None,
    **_: Any,
) -> list[Evaluation]:
    del input, metadata
    outcome = TaskOutcome[Any].model_validate(output)
    if outcome.status != OutcomeStatus.COMPLETED:
        return _failed_speech_scores(
            outcome,
            {
                "der": 1.0,
                "der_no_overlap": 1.0,
                "jer": 1.0,
                "speaker_count_accuracy": 0.0,
            },
        )

    from pyannote.core import Annotation, Segment
    from pyannote.metrics.diarization import DiarizationErrorRate, JaccardErrorRate

    reference = _annotation(expected_output, Annotation, Segment)
    hypothesis = _annotation(outcome.payload, Annotation, Segment)
    evaluations: list[Evaluation] = []
    for suffix, skip_overlap in (("", False), ("_no_overlap", True)):
        metric = DiarizationErrorRate(collar=0.25, skip_overlap=skip_overlap)
        detail = metric(reference, hypothesis, detailed=True)
        evaluations.append(
            Evaluation(
                name=f"der{suffix}",
                value=float(detail["diarization error rate"]),
                metadata={
                    "collar_seconds": 0.25,
                    "skip_overlap": skip_overlap,
                    "engine": "pyannote.metrics",
                    "gated": True,
                },
            )
        )
        if not skip_overlap:
            total = max(float(detail["total"]), 1e-12)
            evaluations.extend(
                [
                    Evaluation(
                        name="missed_speech_rate", value=float(detail["missed detection"]) / total
                    ),
                    Evaluation(name="false_alarm_rate", value=float(detail["false alarm"]) / total),
                    Evaluation(
                        name="speaker_confusion_rate", value=float(detail["confusion"]) / total
                    ),
                ]
            )
    jer = JaccardErrorRate(collar=0.25, skip_overlap=False)(reference, hypothesis)
    evaluations.append(
        Evaluation(name="jer", value=float(jer), metadata={"engine": "pyannote.metrics"})
    )
    reference_speakers = {str(row["speaker"]) for row in _segments(expected_output)}
    predicted_speakers = {str(row["speaker"]) for row in _segments(outcome.payload)}
    evaluations.extend(
        [
            Evaluation(
                name="speaker_count_accuracy",
                value=float(len(reference_speakers) == len(predicted_speakers)),
            ),
            Evaluation(
                name="speaker_count_mae",
                value=float(abs(len(reference_speakers) - len(predicted_speakers))),
            ),
        ]
    )
    return evaluations


def _transcript_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if "transcript" in value:
            return str(value["transcript"])
        if "segments" in value:
            return " ".join(str(segment.get("text", "")) for segment in value["segments"])
    if isinstance(value, list):
        return " ".join(str(segment.get("text", "")) for segment in value)
    raise ValueError("ASR value must be text or contain transcript/segments")


def _segments(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        value = value.get("segments", [])
    if not isinstance(value, list):
        raise ValueError("diarization value must contain a segment list")
    return [dict(segment) for segment in value]


def _annotation(value: Any, annotation_type: Any, segment_type: Any) -> Any:
    annotation = annotation_type()
    tracks: dict[tuple[float, float], int] = defaultdict(int)
    for row in _segments(value):
        start = float(row.get("t_start", row.get("start")))
        end = float(row.get("t_end", row.get("end")))
        speaker = str(row.get("speaker", row.get("cluster_id")))
        key = (start, end)
        track = tracks[key]
        tracks[key] += 1
        annotation[segment_type(start, end), track] = speaker
    return annotation
