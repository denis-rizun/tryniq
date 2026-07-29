from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from langfuse import Langfuse, RunnerContext

from tryniq_evals.contracts import RunPurpose, SuiteDefinition
from tryniq_evals.environment import EvaluationScope
from tryniq_evals.run_metadata import collect_run_metadata


def item_input(item: Any) -> Any:
    return item.get("input") if isinstance(item, dict) else item.input


def prompt_identity(identity: Any) -> str:
    return f"{identity.name}@{identity.version}:sha256:{identity.sha256}"


def run_metadata(
    definition: SuiteDefinition,
    *,
    judge: bool = False,
    model_id: str | None = None,
    embedding_model_id: str | None = None,
    metric_versions: dict[str, str] | None = None,
    prompt_identities: dict[str, str] | None = None,
    rubric_versions: dict[str, str] | None = None,
    decoding_configuration: dict[str, Any] | None = None,
    retrieval_configuration: dict[str, Any] | None = None,
) -> dict[str, str]:
    EvaluationScope.from_environment()
    eval_root = Path(__file__).resolve().parents[3]
    repository_root = eval_root.parent
    checksum = os.environ.get("EVAL_DATASET_CHECKSUM")
    if not checksum:
        raise ValueError("EVAL_DATASET_CHECKSUM is required for immutable experiment runs")
    purpose = RunPurpose(os.environ.get("EVAL_RUN_PURPOSE", RunPurpose.LOCAL))
    metadata = collect_run_metadata(
        definition,
        dataset_checksum=checksum,
        purpose=purpose,
        repository_root=repository_root,
        eval_root=eval_root,
        model_provider=os.environ.get("AI_PROVIDER"),
        model_id=model_id,
        embedding_model_id=embedding_model_id,
        prompt_identities=prompt_identities,
        rubric_versions=rubric_versions,
        metric_versions=metric_versions,
        decoding_configuration=decoding_configuration,
        retrieval_configuration=retrieval_configuration,
    )
    if judge and not metadata.judge_model:
        raise ValueError("EVAL_JUDGE_MODEL is required")
    return metadata.langfuse_metadata()


def local_context(dataset_name: str) -> RunnerContext:
    client = Langfuse()
    dataset = client.get_dataset(dataset_name)
    return RunnerContext(client=client, data=list(dataset.items), dataset_version=dataset.version)


def print_result(result: Any) -> None:
    print(result.format())
    if not result.dataset_run_url:
        raise RuntimeError("dataset-backed experiment did not return a Langfuse run URL")


def qualify_release(result: Any, definition: SuiteDefinition) -> None:
    if os.environ.get("EVAL_RUN_PURPOSE") != RunPurpose.RELEASE:
        return
    from tryniq_evals.gates.loader import load_exceptions, load_policies
    from tryniq_evals.gates.release import apply_release_gates, fetch_baseline_scores

    eval_root = Path(__file__).resolve().parents[3]
    policies = load_policies(eval_root / "gates" / "suites.yaml")
    if definition.suite not in policies:
        raise ValueError(f"no release gate policy exists for suite {definition.suite!r}")
    policy = policies[definition.suite]
    baseline_scores = (
        fetch_baseline_scores(
            Langfuse(),
            dataset_name=definition.dataset_name,
            baseline_run_id=policy.baseline_run_id,
        )
        if policy.baseline_run_id
        else None
    )
    apply_release_gates(
        result,
        policy,
        baseline_scores=baseline_scores,
        exceptions=load_exceptions(eval_root / "gates" / "exceptions.yaml"),
    )
