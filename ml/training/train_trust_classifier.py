from dataclasses import dataclass


@dataclass
class TrustClassifierTrainingConfig:
    backbone: str = "microsoft/layoutlmv3-base"
    epochs: int = 5
    batch_size: int = 4
    learning_rate: float = 2e-5


def main() -> None:
    print("Scaffold only: fine-tune trust/tamper classifier here.")


if __name__ == "__main__":
    main()
