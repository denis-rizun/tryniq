from tryniq_evals.contracts import RunPurpose
from tryniq_evals.run_metadata import HardwareProfile, RunMetadata


def test_langfuse_metadata_flattens_nested_values() -> None:
    metadata = RunMetadata(
        suite="synthetic",
        suite_version="1.0.0",
        dataset_name="tryniq/synthetic/1.0.0/smoke",
        dataset_checksum="a" * 64,
        git_sha="abc123",
        git_dirty=True,
        application_environment="EVAL",
        dependency_lock_checksum="b" * 64,
        random_seed=17,
        concurrency=4,
        run_purpose=RunPurpose.LOCAL,
        hardware=HardwareProfile(
            os="Darwin",
            architecture="arm64",
            cpu="Apple Silicon",
            total_ram_bytes=16,
            runtime_versions={"python": "3.13"},
            model_state="not-applicable",
        ),
        prompt_identities={"chat": "chat@1:sha256:abc"},
    ).langfuse_metadata()

    assert metadata["hardware.os"] == "Darwin"
    assert metadata["hardware.runtime_versions.python"] == "3.13"
    assert metadata["prompt_identities.chat"] == "chat@1:sha256:abc"
    assert "hardware" not in metadata
