import argparse
import json
from dataclasses import dataclass

from ml.training.common import add_common_training_args


@dataclass
class TrustClassifierTrainingConfig:
    backbone: str = "microsoft/layoutlmv3-base"
    epochs: int = 5
    batch_size: int = 4
    learning_rate: float = 2e-5
    seed: int = 42


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune LayoutLMv3 for Sentra structural trust classification.")
    add_common_training_args(parser)
    parser.add_argument("--backbone", default="microsoft/layoutlmv3-base")
    parser.add_argument("--ocr-engine", default="TrOCR")
    return parser.parse_args(argv)


def build_training_plan(args: argparse.Namespace) -> dict:
    config = TrustClassifierTrainingConfig(
        backbone=args.backbone,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        seed=args.seed,
    )
    return {
        "task": "structural_trust_classification",
        "backbone": config.backbone,
        "dataset_manifest": str(args.dataset_manifest),
        "output_dir": str(args.output_dir),
        "ocr_engine": args.ocr_engine,
        "labels": ["coherent", "tampered", "review"],
        "trainer": {
            "epochs": config.epochs,
            "batch_size": config.batch_size,
            "learning_rate": config.learning_rate,
            "seed": config.seed,
        },
        "checkpoint_pattern": str(args.output_dir / "checkpoints" / "trust_classifier_epoch_{epoch}.pt"),
    }


def main() -> None:
    args = parse_args()
    print(json.dumps(build_training_plan(args), indent=2))


if __name__ == "__main__":
    main()
