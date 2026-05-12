from pathlib import Path

from ml.evaluation.evaluate_pipeline import build_evaluation_plan, parse_args


def test_evaluation_plan_tracks_expected_outputs(tmp_path):
    args = parse_args(
        [
            "--dataset-manifest",
            str(tmp_path / "eval_manifest.json"),
            "--output-report",
            str(tmp_path / "report.json"),
        ]
    )
    plan = build_evaluation_plan(args)

    assert plan["output_report"] == str(tmp_path / "report.json")
    assert "artifact_classification" in plan["tasks"]
    assert "system_latency" in plan["tasks"]
