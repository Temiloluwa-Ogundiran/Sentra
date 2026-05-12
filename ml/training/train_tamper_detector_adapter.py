import argparse
import json


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Adapt and package the tamper detector used in Sentra's research pipeline."
    )
    parser.add_argument("--base-model", default="IrishMehta/fraud-detection-idnet-three-class")
    parser.add_argument("--dataset-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--package-name", default="sentra-tamper-detector")
    return parser.parse_args(argv)


def build_adapter_plan(args: argparse.Namespace) -> dict:
    return {
        "task": "tamper_detector_adaptation",
        "base_model": args.base_model,
        "dataset_manifest": args.dataset_manifest,
        "output_dir": args.output_dir,
        "package_name": args.package_name,
        "steps": [
            "load labeled tamper manifest",
            "map labels into coherent / tampered task space",
            "export adapter-ready configuration",
            "package inference metadata for hosted deployment",
        ],
    }


def main() -> None:
    args = parse_args()
    print(json.dumps(build_adapter_plan(args), indent=2))


if __name__ == "__main__":
    main()
