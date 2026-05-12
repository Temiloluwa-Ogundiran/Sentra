from dataclasses import dataclass


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    source: str
    purpose: str
    task_family: str
    license_note: str


DATASETS: dict[str, DatasetSpec] = {
    "cord": DatasetSpec(
        name="cord",
        source="https://github.com/clovaai/cord",
        purpose="receipt structure and field layout supervision",
        task_family="receipt_understanding",
        license_note="Check upstream licensing before redistribution.",
    ),
    "sroie": DatasetSpec(
        name="sroie",
        source="https://mindspore-lab.github.io/mindocr/datasets/sroie/",
        purpose="receipt OCR and key information extraction",
        task_family="receipt_ocr",
        license_note="Use according to the upstream competition terms.",
    ),
    "find_it_again": DatasetSpec(
        name="find_it_again",
        source="https://l3i-share.univ-lr.fr/2023Finditagain/index.html",
        purpose="forged receipt supervision",
        task_family="receipt_forgery",
        license_note="Check dataset terms before packaging samples.",
    ),
    "doctamper": DatasetSpec(
        name="doctamper",
        source="https://github.com/qcf-568/DocTamper",
        purpose="document tampering supervision",
        task_family="tamper_detection",
        license_note="Use according to upstream repository instructions.",
    ),
    "local_references": DatasetSpec(
        name="local_references",
        source="local_curated",
        purpose="anonymized Nigerian payment-proof references",
        task_family="domain_adaptation",
        license_note="Keep all artifacts anonymized and access-controlled.",
    ),
    "synthetic_tampered": DatasetSpec(
        name="synthetic_tampered",
        source="generated_from_local_and_public",
        purpose="tampered variants derived from clean references",
        task_family="tamper_detection",
        license_note="Generated artifacts inherit constraints from source datasets.",
    ),
}


def list_datasets() -> dict[str, DatasetSpec]:
    return DATASETS.copy()


def get_dataset(name: str) -> DatasetSpec:
    return DATASETS[name]


def build_default_dataset_groups() -> dict[str, list[str]]:
    return {
        "public_supervision": ["cord", "sroie", "find_it_again", "doctamper"],
        "local_nigerian_references": ["local_references"],
        "synthetic_tampering": ["synthetic_tampered"],
    }
