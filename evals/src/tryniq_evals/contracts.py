from __future__ import annotations

from collections.abc import Awaitable, Callable
from enum import StrEnum
from time import perf_counter
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OutcomeStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class FailureCategory(StrEnum):
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    TIMEOUT = "timeout"
    PROVIDER_RATE_LIMIT = "provider_rate_limit"
    VALIDATION_SCHEMA = "validation_schema"
    INVARIANT = "invariant"
    INFRASTRUCTURE = "infrastructure"
    UNEXPECTED = "unexpected"


class SkipConstraint(StrEnum):
    HARDWARE = "hardware"
    LICENSE = "license"


class RunPurpose(StrEnum):
    LOCAL = "local"
    PR = "pr"
    NIGHTLY = "nightly"
    RELEASE = "release"
    BENCHMARK = "benchmark"
    ONLINE_BACKFILL = "online-backfill"


class Cadence(StrEnum):
    LOCAL = "local"
    PR = "pr"
    NIGHTLY = "nightly"
    WEEKLY = "weekly"
    RELEASE = "release"
    ONLINE = "online"


class HardwareRequirement(StrEnum):
    CPU = "cpu"
    APPLE_SILICON = "apple-silicon"
    CUDA = "cuda"
    STREAMER = "swift-streamer"


class AttachmentReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    uri: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    media_type: str | None = None

    @model_validator(mode="after")
    def validate_logical_uri(self) -> Self:
        lowered = self.uri.lower()
        if lowered.startswith(("/", "file://")) or "x-amz-signature=" in lowered:
            raise ValueError("attachments must use logical, non-expiring URIs")
        if "://" not in self.uri:
            raise ValueError("attachments must use a logical URI with a scheme")
        return self


class DatasetItemMetadata(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    stable_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    split: str = Field(pattern=r"^(smoke|development|test|holdout|adversarial)$")
    license: str = Field(min_length=1)
    tags: tuple[str, ...] = ()
    difficulty: str | None = None
    language: str | None = None
    annotation_provenance: str = Field(min_length=1)
    annotator: str | None = None
    second_reviewer: str | None = None
    meeting_group: str | None = None


class DatasetEnvelope[InputT, ExpectedT](BaseModel):
    model_config = ConfigDict(frozen=True)

    input: InputT
    expected_output: ExpectedT
    metadata: DatasetItemMetadata
    attachments: tuple[AttachmentReference, ...] = ()


class OperationalMeasurements(BaseModel):
    model_config = ConfigDict(frozen=True)

    latency_ms: float | None = Field(default=None, ge=0)
    time_to_first_token_ms: float | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    peak_memory_mb: float | None = Field(default=None, ge=0)
    retry_count: int = Field(default=0, ge=0)
    fallback_used: bool = False


class FailureDetail(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: FailureCategory
    message: str
    exception_type: str | None = None


class SkipDetail(BaseModel):
    model_config = ConfigDict(frozen=True)

    constraint: SkipConstraint
    reason: str


class TaskOutcome[PayloadT](BaseModel):
    model_config = ConfigDict(frozen=True)

    status: OutcomeStatus
    payload: PayloadT | None = None
    failure: FailureDetail | None = None
    skip: SkipDetail | None = None
    measurements: OperationalMeasurements = Field(default_factory=OperationalMeasurements)

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.status == OutcomeStatus.COMPLETED and self.failure is None and self.skip is None:
            return self
        if self.status == OutcomeStatus.FAILED and self.failure is not None and self.skip is None:
            return self
        if self.status == OutcomeStatus.SKIPPED and self.skip is not None and self.failure is None:
            return self
        raise ValueError("TaskOutcome status does not match its failure/skip fields")

    @classmethod
    def completed(
        cls,
        payload: PayloadT,
        *,
        measurements: OperationalMeasurements | None = None,
    ) -> TaskOutcome[PayloadT]:
        return cls(
            status=OutcomeStatus.COMPLETED,
            payload=payload,
            measurements=measurements or OperationalMeasurements(),
        )

    @classmethod
    def failed(
        cls,
        category: FailureCategory,
        message: str,
        *,
        exception_type: str | None = None,
        measurements: OperationalMeasurements | None = None,
    ) -> TaskOutcome[PayloadT]:
        return cls(
            status=OutcomeStatus.FAILED,
            failure=FailureDetail(
                category=category,
                message=message,
                exception_type=exception_type,
            ),
            measurements=measurements or OperationalMeasurements(),
        )

    @classmethod
    def skipped(
        cls,
        constraint: SkipConstraint,
        reason: str,
    ) -> TaskOutcome[PayloadT]:
        return cls(
            status=OutcomeStatus.SKIPPED,
            skip=SkipDetail(constraint=constraint, reason=reason),
        )


class GateDirection(StrEnum):
    MIN = "min"
    MAX = "max"
    EXACT = "exact"


class MetricGate(BaseModel):
    model_config = ConfigDict(frozen=True)

    metric: str
    direction: GateDirection
    threshold: float
    primary: bool = False
    hard_invariant: bool = False
    relative_regression_limit: float | None = Field(default=None, ge=0)


class SuiteDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    suite: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    dataset_name: str
    concurrency: int = Field(ge=1)
    cadence: tuple[Cadence, ...]
    required_hardware: tuple[HardwareRequirement, ...] = (HardwareRequirement.CPU,)
    evaluators: tuple[str, ...]
    gates: tuple[MetricGate, ...] = ()
    owner: str
    informational_only: bool = False
    judge_metrics: bool = False

    @model_validator(mode="after")
    def validate_dataset_name(self) -> Self:
        expected_prefix = f"tryniq/{self.suite}/{self.version}/"
        if not self.dataset_name.startswith(expected_prefix):
            raise ValueError(f"dataset_name must start with {expected_prefix!r}")
        if self.dataset_name.rsplit("/", 1)[-1] not in {
            "smoke",
            "development",
            "test",
            "holdout",
            "adversarial",
        }:
            raise ValueError("dataset_name must end in an approved immutable split")
        return self


class DeclaredSkip(Exception):
    def __init__(self, constraint: SkipConstraint, reason: str) -> None:
        super().__init__(reason)
        self.constraint = constraint
        self.reason = reason


def classify_exception(exc: Exception) -> FailureCategory:
    name = type(exc).__name__.lower()
    module = type(exc).__module__.lower()
    if isinstance(exc, (TimeoutError,)) or "timeout" in name:
        return FailureCategory.TIMEOUT
    if (
        isinstance(exc, (ImportError, ModuleNotFoundError))
        or "dependency" in name
        or "unavailable" in name
    ):
        return FailureCategory.DEPENDENCY_UNAVAILABLE
    if "ratelimit" in name or "rate_limit" in name or "provider" in module and "limit" in name:
        return FailureCategory.PROVIDER_RATE_LIMIT
    if "validation" in name or "schema" in name:
        return FailureCategory.VALIDATION_SCHEMA
    if isinstance(exc, AssertionError) or "invariant" in name:
        return FailureCategory.INVARIANT
    if isinstance(exc, (ConnectionError, OSError)) or "redis" in module or "sqlalchemy" in module:
        return FailureCategory.INFRASTRUCTURE
    return FailureCategory.UNEXPECTED


async def capture_task[PayloadT](
    call: Callable[[], Awaitable[PayloadT]],
) -> TaskOutcome[PayloadT]:
    started = perf_counter()
    try:
        payload = await call()
    except DeclaredSkip as exc:
        return TaskOutcome.skipped(exc.constraint, exc.reason)
    except Exception as exc:  # The experiment must retain every attempted item.
        return TaskOutcome.failed(
            classify_exception(exc),
            str(exc) or type(exc).__name__,
            exception_type=f"{type(exc).__module__}.{type(exc).__name__}",
            measurements=OperationalMeasurements(latency_ms=(perf_counter() - started) * 1000),
        )
    return TaskOutcome.completed(
        payload,
        measurements=OperationalMeasurements(latency_ms=(perf_counter() - started) * 1000),
    )
