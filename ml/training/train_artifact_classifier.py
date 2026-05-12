import argparse
import json
from dataclasses import asdict, dataclass

from ml.training.common import add_common_training_args


@dataclass
class ArtifactClassifierTrainingConfig:
    backbone: str = "microsoft/dit-base"
    epochs: int = 5
    batch_size: int = 8
    learning_rate: float = 2e-5
    seed: int = 42


ARTIFACT_LABELS = [
    "bank_alert_screenshot",
    "sms_alert_screenshot",
    "payment_receipt_screenshot",
    "receipt_pdf_render",
    "unknown",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune DiT for Sentra artifact classification.")
    add_common_training_args(parser)
    parser.add_argument("--backbone", default="microsoft/dit-base")
    return parser.parse_args(argv)


def build_training_plan(args: argparse.Namespace) -> dict:
    config = ArtifactClassifierTrainingConfig(
        backbone=args.backbone,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        seed=args.seed,
    )
    return {
        "task": "artifact_classification",
        "backbone": config.backbone,
        "dataset_manifest": str(args.dataset_manifest),
        "output_dir": str(args.output_dir),
        "labels": ARTIFACT_LABELS,
        "trainer": {
            "epochs": config.epochs,
            "batch_size": config.batch_size,
            "learning_rate": config.learning_rate,
            "seed": config.seed,
        },
        "checkpoint_pattern": str(args.output_dir / "checkpoints" / "artifact_classifier_epoch_{epoch}.pt"),
    }


def main() -> None:
    args = parse_args()
    print(json.dumps(build_training_plan(args), indent=2))


if __name__ == "__main__":
    main()
