import asyncio

import pytest
from pydantic import ValidationError

from tryniq_evals.contracts import (
    AttachmentReference,
    Cadence,
    DeclaredSkip,
    FailureCategory,
    OutcomeStatus,
    SkipConstraint,
    SuiteDefinition,
    TaskOutcome,
    capture_task,
)


def test_task_outcome_rejects_inconsistent_state() -> None:
    with pytest.raises(ValidationError):
        TaskOutcome(status=OutcomeStatus.FAILED)


@pytest.mark.parametrize("uri", ["/tmp/audio.wav", "file:///tmp/audio.wav", "audio.wav"])
def test_attachment_rejects_local_or_non_logical_uris(uri: str) -> None:
    with pytest.raises(ValidationError):
        AttachmentReference(uri=uri, sha256="0" * 64)


def test_suite_requires_versioned_immutable_dataset_name() -> None:
    with pytest.raises(ValidationError):
        SuiteDefinition(
            suite="rag-answer",
            version="1.0.0",
            dataset_name="tryniq/rag-answer/latest/test",
            concurrency=1,
            cadence=(Cadence.LOCAL,),
            evaluators=("answer",),
            owner="ai",
        )


@pytest.mark.asyncio
async def test_capture_task_retains_typed_failures_and_declared_skips() -> None:
    async def timeout() -> None:
        raise TimeoutError("slow")

    async def skip() -> None:
        raise DeclaredSkip(SkipConstraint.HARDWARE, "CUDA host required")

    failed = await capture_task(timeout)
    skipped = await capture_task(skip)
    assert failed.status == OutcomeStatus.FAILED
    assert failed.failure.category == FailureCategory.TIMEOUT
    assert failed.measurements.latency_ms is not None
    assert skipped.status == OutcomeStatus.SKIPPED
    assert skipped.skip.constraint == SkipConstraint.HARDWARE


@pytest.mark.asyncio
async def test_capture_task_is_concurrency_safe() -> None:
    async def value(index: int) -> int:
        await asyncio.sleep(0)
        return index

    outcomes = await asyncio.gather(*(capture_task(lambda i=i: value(i)) for i in range(20)))
    assert [outcome.payload for outcome in outcomes] == list(range(20))
