import argparse
import json
from pathlib import Path

from PIL import Image


def generate_tampered_sample(
    *,
    source_path: Path,
    output_dir: Path,
    operation: str,
    label: str,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{source_path.stem}_{operation}.png"

    with Image.open(source_path) as image:
        if operation == "compression_variant":
            image.save(target, format="PNG", optimize=True)
        elif operation == "crop_variant":
            width, height = image.size
            image.crop((0, 0, int(width * 0.9), int(height * 0.9))).save(target)
        else:
            image.save(target)

    return {
        "artifact_path": str(target),
        "label": label,
        "metadata": {"operation": operation, "source_path": str(source_path)},
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic tampered variants from clean artifacts.")
    parser.add_argument("--source", type=Path, required=True, help="Path to a clean artifact image.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for generated outputs.")
    parser.add_argument("--operation", default="compression_variant")
    parser.add_argument("--label", default="tampered")
    parser.add_argument("--manifest-out", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generated = generate_tampered_sample(
        source_path=args.source,
        output_dir=args.output_dir,
        operation=args.operation,
        label=args.label,
    )
    if args.manifest_out:
        args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_out.write_text(json.dumps(generated, indent=2), encoding="utf-8")
    print(json.dumps(generated, indent=2))


if __name__ == "__main__":
    main()
