from dataclasses import dataclass


@dataclass
class ArtifactClassifierTrainingConfig:
    backbone: str = "microsoft/dit-base"
    epochs: int = 5
    batch_size: int = 8
    learning_rate: float = 2e-5


def main() -> None:
    print("Scaffold only: fine-tune artifact classifier here.")


if __name__ == "__main__":
    main()
