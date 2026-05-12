import argparse
import json


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Sentra model and system tasks from a dataset manifest.")
    parser.add_argument("--dataset-manifest", required=True)
    parser.add_argument("--output-report", required=True)
    parser.add_argument(
        "--tasks",
        nargs="+",
        default=["artifact_classification", "tamper_detection", "system_latency"],
    )
    return parser.parse_args(argv)


def build_evaluation_plan(args: argparse.Namespace) -> dict:
    return {
        "dataset_manifest": args.dataset_manifest,
        "output_report": args.output_report,
        "tasks": args.tasks,
        "metrics": {
            "artifact_classification": ["accuracy", "confusion_matrix"],
            "tamper_detection": ["precision", "recall", "f1"],
            "system_latency": ["p50_ms", "p95_ms"],
        },
    }


def main() -> None:
    args = parse_args()
    print(json.dumps(build_evaluation_plan(args), indent=2))


if __name__ == "__main__":
    main()
