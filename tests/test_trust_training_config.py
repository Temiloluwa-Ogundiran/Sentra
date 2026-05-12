from pathlib import Path

from ml.training.train_trust_classifier import build_training_plan, parse_args


def test_trust_training_plan_uses_layoutlmv3(tmp_path):
    args = parse_args(
        [
            "--dataset-manifest",
            str(tmp_path / "trust_manifest.json"),
            "--output-dir",
            str(tmp_path / "trust_outputs"),
        ]
    )
    plan = build_training_plan(args)

    assert plan["backbone"] == "microsoft/layoutlmv3-base"
    assert plan["output_dir"] == str(tmp_path / "trust_outputs")
    assert plan["task"] == "structural_trust_classification"
