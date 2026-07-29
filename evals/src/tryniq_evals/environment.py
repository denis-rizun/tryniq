from __future__ import annotations

import os
import re
from pathlib import PurePosixPath
from urllib.parse import urlparse
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, model_validator


class UnsafeEvaluationEnvironment(RuntimeError):
    """Raised before an experiment can touch application infrastructure."""


class EvaluationScope(BaseModel):
    model_config = ConfigDict(frozen=True)

    application_environment: str
    database_name: str
    bucket: str
    object_prefix: str
    redis_url: str
    redis_namespace: str
    langfuse_environment: str

    @model_validator(mode="after")
    def require_visible_evaluation_scope(self) -> EvaluationScope:
        failures: list[str] = []
        if self.application_environment.upper() != "EVAL":
            failures.append("ENV must be EVAL")
        if "eval" not in self.database_name.lower():
            failures.append("Postgres database name must contain 'eval'")
        if "eval" not in f"{self.bucket}/{self.object_prefix}".lower():
            failures.append("MinIO bucket or prefix must contain 'eval'")

        parsed = urlparse(self.redis_url)
        redis_db = parsed.path.lstrip("/")
        if redis_db in {"", "0"}:
            failures.append("Redis must use a non-default database")
        if "eval" not in self.redis_namespace.lower():
            failures.append("Redis namespace must contain 'eval'")
        if "eval" not in self.langfuse_environment.lower():
            failures.append("Langfuse environment must contain 'eval'")
        if failures:
            raise ValueError("; ".join(failures))
        return self

    @classmethod
    def from_environment(cls) -> EvaluationScope:
        try:
            return cls(
                application_environment=os.environ.get("ENV", ""),
                database_name=os.environ.get("POSTGRES_DATABASE", ""),
                bucket=os.environ.get("MINIO_BUCKET", ""),
                object_prefix=os.environ.get("EVAL_MINIO_PREFIX", ""),
                redis_url=os.environ.get("REDIS_URL", ""),
                redis_namespace=os.environ.get("EVAL_REDIS_NAMESPACE", ""),
                langfuse_environment=os.environ.get(
                    "LANGFUSE_TRACING_ENVIRONMENT",
                    os.environ.get("LANGFUSE_ENVIRONMENT", ""),
                ),
            )
        except ValueError as exc:
            raise UnsafeEvaluationEnvironment(str(exc)) from exc


_SAFE_ID = re.compile(r"[^a-zA-Z0-9._-]+")


class RunScope(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str = Field(min_length=1)
    object_root: str = "eval-runs"

    def fixture_meeting_id(self, stable_item_id: str) -> UUID:
        return uuid5(
            UUID("d2c5b565-4936-4e37-9435-61ad752a74db"), f"{self.run_id}:{stable_item_id}"
        )

    def object_prefix(self, stable_item_id: str | None = None) -> str:
        run = _SAFE_ID.sub("-", self.run_id).strip("-")
        parts = [self.object_root, run]
        if stable_item_id is not None:
            item = _SAFE_ID.sub("-", stable_item_id).strip("-")
            parts.append(item)
        return str(PurePosixPath(*parts)) + "/"

    def validate_cleanup_prefix(self, prefix: str) -> None:
        expected = self.object_prefix()
        if not prefix.startswith(expected) or prefix == self.object_root:
            raise UnsafeEvaluationEnvironment(
                f"cleanup prefix {prefix!r} is outside resolved run scope {expected!r}"
            )
