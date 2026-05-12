from pathlib import Path

from ml.datasets.catalog import build_default_dataset_groups, get_dataset, list_datasets
from ml.datasets.manifest import DatasetManifest, DatasetManifestEntry


def test_dataset_catalog_contains_expected_specs():
    datasets = list_datasets()
    assert "cord" in datasets
    assert get_dataset("doctamper").task_family == "tamper_detection"


def test_dataset_manifest_roundtrip(tmp_path):
    manifest = DatasetManifest(
        entries=[
            DatasetManifestEntry(
                dataset_name="local_references",
                split="train",
                artifact_path="data/train/proof1.png",
                label="bank_alert_screenshot",
                metadata={"source": "local"},
            ),
            DatasetManifestEntry(
                dataset_name="synthetic_tampered",
                split="test",
                artifact_path="data/test/proof2.png",
                label="tampered",
                metadata={"edit_type": "amount"},
            ),
        ]
    )

    target = tmp_path / "manifest.json"
    manifest.save(target)
    loaded = DatasetManifest.load(target)

    assert loaded.split_counts() == {"train": 1, "test": 1}
    assert loaded.entries[1].metadata["edit_type"] == "amount"


def test_default_dataset_groups_include_public_and_local_layers():
    groups = build_default_dataset_groups()
    assert "public_supervision" in groups
    assert "local_nigerian_references" in groups
