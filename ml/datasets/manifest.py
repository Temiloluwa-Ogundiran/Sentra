import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class DatasetManifestEntry:
    dataset_name: str
    split: str
    artifact_path: str
    label: str
    metadata: dict = field(default_factory=dict)


@dataclass
class DatasetManifest:
    entries: list[DatasetManifestEntry] = field(default_factory=list)

    def save(self, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {"entries": [asdict(entry) for entry in self.entries]}
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, source: Path) -> "DatasetManifest":
        payload = json.loads(source.read_text(encoding="utf-8"))
        return cls(entries=[DatasetManifestEntry(**entry) for entry in payload.get("entries", [])])

    def split_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in self.entries:
            counts[entry.split] = counts.get(entry.split, 0) + 1
        return counts
