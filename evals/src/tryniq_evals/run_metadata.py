from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tryniq_evals.contracts import RunPurpose, SuiteDefinition


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class HardwareProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    os: str
    architecture: str
    cpu: str
    total_ram_bytes: int | None = None
    accelerator: str | None = None
    accelerator_memory_bytes: int | None = None
    runtime_versions: dict[str, str] = Field(default_factory=dict)
    model_state: str = Field(pattern=r"^(cold|warm|not-applicable)$")

    @classmethod
    def detect(cls, *, model_state: str = "not-applicable") -> HardwareProfile:
        total_ram: int | None = None
        try:
            page_size = os.sysconf("SC_PAGE_SIZE")
            pages = os.sysconf("SC_PHYS_PAGES")
            total_ram = int(page_size * pages)
        except (AttributeError, OSError, ValueError):
            pass
        return cls(
            os=f"{platform.system()} {platform.release()}",
            architecture=platform.machine(),
            cpu=platform.processor() or platform.machine(),
            total_ram_bytes=total_ram,
            model_state=model_state,
        )


class RunMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    suite: str
    suite_version: str
    dataset_name: str
    dataset_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    git_sha: str
    git_dirty: bool
    application_environment: str
    dependency_lock_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    random_seed: int
    concurrency: int
    run_purpose: RunPurpose
    hardware: HardwareProfile
    model_provider: str | None = None
    model_id: str | None = None
    embedding_model_id: str | None = None
    prompt_identities: dict[str, str] = Field(default_factory=dict)
    judge_model: str | None = None
    rubric_versions: dict[str, str] = Field(default_factory=dict)
    metric_versions: dict[str, str] = Field(default_factory=dict)
    decoding_configuration: dict[str, Any] = Field(default_factory=dict)
    retrieval_configuration: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_self_judging(self) -> RunMetadata:
        if self.run_purpose == RunPurpose.RELEASE and self.judge_model:
            if self.model_id and self.judge_model.casefold() == self.model_id.casefold():
                raise ValueError("release qualification cannot use the model under test as judge")
        return self

    def langfuse_metadata(self) -> dict[str, str]:
        raw = self.model_dump(mode="json")
        flattened: dict[str, str] = {}

        def add(prefix: str, value: Any) -> None:
            if isinstance(value, dict):
                if not value:
                    flattened[prefix] = "{}"
                    return
                for nested_key, nested_value in sorted(value.items()):
                    add(f"{prefix}.{nested_key}", nested_value)
                return
            if isinstance(value, list):
                flattened[prefix] = json.dumps(value, sort_keys=True)
                return
            flattened[prefix] = value if isinstance(value, str) else json.dumps(value)

        for key, value in raw.items():
            add(key, value)
        return flattened


def collect_run_metadata(
    definition: SuiteDefinition,
    *,
    dataset_checksum: str,
    purpose: RunPurpose,
    repository_root: Path,
    eval_root: Path,
    random_seed: int = 17,
    model_provider: str | None = None,
    model_id: str | None = None,
    embedding_model_id: str | None = None,
    prompt_identities: dict[str, str] | None = None,
    rubric_versions: dict[str, str] | None = None,
    metric_versions: dict[str, str] | None = None,
    decoding_configuration: dict[str, Any] | None = None,
    retrieval_configuration: dict[str, Any] | None = None,
    model_state: str = "not-applicable",
) -> RunMetadata:
    judge_model = os.environ.get("EVAL_JUDGE_MODEL")
    if definition.judge_metrics and not judge_model:
        raise ValueError("EVAL_JUDGE_MODEL is required for suites with semantic judges")
    return RunMetadata(
        suite=definition.suite,
        suite_version=definition.version,
        dataset_name=definition.dataset_name,
        dataset_checksum=dataset_checksum,
        git_sha=_git("rev-parse", "HEAD", cwd=repository_root),
        git_dirty=bool(_git("status", "--porcelain", cwd=repository_root)),
        application_environment=os.environ.get("ENV", ""),
        dependency_lock_checksum=sha256_file(eval_root / "uv.lock"),
        random_seed=random_seed,
        concurrency=definition.concurrency,
        run_purpose=purpose,
        hardware=HardwareProfile.detect(model_state=model_state),
        model_provider=model_provider,
        model_id=model_id,
        embedding_model_id=embedding_model_id,
        prompt_identities=prompt_identities or {},
        judge_model=judge_model,
        rubric_versions=rubric_versions or {},
        metric_versions=metric_versions or {},
        decoding_configuration=decoding_configuration or {},
        retrieval_configuration=retrieval_configuration or {},
    )
