from pathlib import Path

from ml.training.train_artifact_classifier import build_training_plan, parse_args


def test_artifact_training_plan_uses_dit_backbone(tmp_path):
    args = parse_args(
        [
            "--dataset-manifest",
            str(tmp_path / "artifact_manifest.json"),
            "--output-dir",
            str(tmp_path / "artifacts"),
        ]
    )
    plan = build_training_plan(args)

    assert plan["backbone"] == "microsoft/dit-base"
    assert plan["output_dir"] == str(tmp_path / "artifacts")
    assert "bank_alert_screenshot" in plan["labels"]
