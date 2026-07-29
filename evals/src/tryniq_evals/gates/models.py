from __future__ import annotations

from datetime import date
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tryniq_evals.contracts import GateDirection, MetricGate


class SuiteGatePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    suite: str
    baseline_run_id: str | None = None
    gates: tuple[MetricGate, ...]
    latency_regression_limit: float = Field(default=0.10, ge=0)
    cost_regression_limit: float = Field(default=0.15, ge=0)
    quality_regression_limit: float = Field(default=0.03, ge=0)
    require_complete_metadata: bool = True


class GateException(BaseModel):
    model_config = ConfigDict(frozen=True)

    suite: str
    metric: str
    owner: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    langfuse_run_url: str
    failing_slices: tuple[str, ...]
    expires: date

    @model_validator(mode="after")
    def require_immutable_run_link(self) -> Self:
        if not self.langfuse_run_url.startswith(("http://", "https://")):
            raise ValueError("exception must link to an immutable Langfuse run")
        return self

    def active_on(self, day: date) -> bool:
        return day <= self.expires


class GateFailure(BaseModel):
    model_config = ConfigDict(frozen=True)

    metric: str
    value: float | None
    threshold: float | None
    reason: str
    direction: GateDirection | None = None
