from pathlib import Path

from PIL import Image

from ml.datasets.manifest import DatasetManifestEntry
from ml.datasets.synthetic_ops import build_variant_plan
from scripts.generate_synthetic.generate_tampered_samples import generate_tampered_sample


def test_build_variant_plan_contains_expected_operations():
    entry = DatasetManifestEntry(
        dataset_name="local_references",
        split="train",
        artifact_path="data/proof.png",
        label="bank_alert_screenshot",
        metadata={"provider": "demo-bank"},
    )

    plan = build_variant_plan(entry)

    assert "amount_edit" in plan
    assert "compression_variant" in plan
    assert "crop_variant" in plan


def test_generate_tampered_sample_writes_image_and_metadata(tmp_path):
    source = tmp_path / "proof.png"
    Image.new("RGB", (900, 1200), color="white").save(source)

    output_dir = tmp_path / "output"
    generated = generate_tampered_sample(
        source_path=source,
        output_dir=output_dir,
        operation="compression_variant",
        label="tampered",
    )

    assert Path(generated["artifact_path"]).exists()
    assert generated["metadata"]["operation"] == "compression_variant"
    assert generated["label"] == "tampered"
