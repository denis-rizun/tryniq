import pytest
from pydantic import ValidationError

from tryniq_evals.environment import EvaluationScope, RunScope, UnsafeEvaluationEnvironment


def valid_scope(**overrides: str) -> EvaluationScope:
    values = {
        "application_environment": "EVAL",
        "database_name": "tryniq_eval",
        "bucket": "tryniq-eval",
        "object_prefix": "eval-runs/",
        "redis_url": "redis://localhost:6379/15",
        "redis_namespace": "tryniq-eval",
        "langfuse_environment": "evaluation",
    }
    values.update(overrides)
    return EvaluationScope(**values)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("application_environment", "PROD"),
        ("database_name", "tryniq"),
        ("bucket", "tryniq"),
        ("object_prefix", "runs"),
        ("redis_url", "redis://localhost:6379/0"),
        ("redis_namespace", "tryniq"),
        ("langfuse_environment", "production"),
    ],
)
def test_environment_guard_rejects_unsafe_scope(field: str, value: str) -> None:
    overrides = {field: value}
    if field in {"bucket", "object_prefix"}:
        overrides.update({"bucket": "tryniq", "object_prefix": "runs"})
    with pytest.raises(ValidationError):
        valid_scope(**overrides)


def test_run_scope_is_deterministic_and_cleanup_is_narrow() -> None:
    scope = RunScope(run_id="run/123")
    assert scope.fixture_meeting_id("item-a") == scope.fixture_meeting_id("item-a")
    assert scope.fixture_meeting_id("item-a") != scope.fixture_meeting_id("item-b")
    prefix = scope.object_prefix("item-a")
    scope.validate_cleanup_prefix(prefix)
    with pytest.raises(UnsafeEvaluationEnvironment):
        scope.validate_cleanup_prefix("eval-runs/")
