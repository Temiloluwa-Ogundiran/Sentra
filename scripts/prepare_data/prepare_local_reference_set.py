import argparse
import json
from pathlib import Path


def build_reference_record(source_path: Path, artifact_type: str) -> dict:
    return {
        "artifact_path": str(source_path),
        "artifact_type": artifact_type,
        "anonymized": True,
        "source_layer": "local_nigerian_references",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index and normalize local Sentra reference artifacts.")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--artifact-type", required=True)
    parser.add_argument("--output-manifest", type=Path, required=True)
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    records = [
        build_reference_record(path, args.artifact_type)
        for path in sorted(args.source_dir.glob("*"))
        if path.is_file()
    ]
    args.output_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.output_manifest.write_text(json.dumps({"entries": records}, indent=2), encoding="utf-8")
    print(json.dumps({"count": len(records), "output_manifest": str(args.output_manifest)}, indent=2))


if __name__ == "__main__":
    main()
