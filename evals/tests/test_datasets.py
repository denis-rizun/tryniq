from pathlib import Path

import pytest

from tryniq_evals.datasets.manifest import (
    SourceManifest,
    canonical_items_checksum,
    deterministic_item_id,
)
from tryniq_evals.datasets.sync import (
    DatasetMismatchError,
    load_envelopes,
    synchronize_dataset,
    validate_governance,
)


class FakeLangfuse:
    def __init__(self, existing=None) -> None:
        self.existing = existing
        self.created_datasets: list[dict] = []
        self.created_items: list[dict] = []
        self.flushed = False

    def get_dataset(self, name: str):
        if self.existing is None:
            raise RuntimeError("dataset not found")
        return self.existing

    def create_dataset(self, **kwargs):
        self.created_datasets.append(kwargs)

    def create_dataset_item(self, **kwargs):
        self.created_items.append(kwargs)

    def flush(self):
        self.flushed = True


def test_synthetic_manifest_checksum_is_reproducible() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = SourceManifest.load(
        root / "datasets/manifests/synthetic-foundation-1.0.0-smoke.yaml"
    )
    items = load_envelopes(root / manifest.items_file)
    assert canonical_items_checksum(items) == manifest.content_checksum
    assert deterministic_item_id(manifest.dataset_name, "foundation-001") == deterministic_item_id(
        manifest.dataset_name, "foundation-001"
    )


def test_sync_aborts_on_published_content_mismatch() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = SourceManifest.load(
        root / "datasets/manifests/synthetic-foundation-1.0.0-smoke.yaml"
    )
    items = load_envelopes(root / manifest.items_file)
    existing = type("Dataset", (), {"metadata": {"content_checksum": "f" * 64}, "items": items})
    with pytest.raises(DatasetMismatchError):
        synchronize_dataset(FakeLangfuse(existing), manifest, items)


def test_sync_creates_deterministic_items_once() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = SourceManifest.load(
        root / "datasets/manifests/synthetic-foundation-1.0.0-smoke.yaml"
    )
    items = load_envelopes(root / manifest.items_file)
    client = FakeLangfuse()
    synchronize_dataset(client, manifest, items)
    assert len(client.created_datasets) == 1
    assert len(client.created_items) == 1
    assert client.created_items[0]["id"] == deterministic_item_id(
        manifest.dataset_name, "foundation-001"
    )
    assert client.flushed


def test_governance_rejects_secret_fields_before_upload() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = SourceManifest.load(
        root / "datasets/manifests/synthetic-foundation-1.0.0-smoke.yaml"
    )
    item = load_envelopes(root / manifest.items_file)[0]
    unsafe = item.model_copy(update={"input": {"api_key": "not-for-langfuse"}})

    with pytest.raises(ValueError, match="forbidden dataset field"):
        validate_governance(manifest, [unsafe])
