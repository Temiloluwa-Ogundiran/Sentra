import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.inference.pipeline import run_pipeline


ARTIFACT_ROOT = Path("artifacts")
EXPECTED = {
    "real": {"High-confidence pattern match"},
    "fake": {"Review", "Suspicious"},
}


def infer_mime_type(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return "application/pdf"
    if path.suffix.lower() in {".png"}:
        return "image/png"
    return "image/jpeg"


def evaluate_folder(folder: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(folder.iterdir()):
        if not path.is_file():
            continue
        result, debug = run_pipeline(
            request_id=1,
            file_path=path,
            mime_type=infer_mime_type(path),
        )
        rows.append(
            {
                "file": str(path),
                "verdict": result.verdict,
                "fields": result.extracted_fields.model_dump(),
                "reasons": result.reasons,
                "processing_time_ms": result.processing_time_ms,
                "passes_expectation": result.verdict in EXPECTED[folder.name],
                "model_scores": debug["model_scores"],
            }
        )
    return rows


def main() -> None:
    summary: dict[str, list[dict]] = {}
    for name in ("real", "fake"):
        folder = ARTIFACT_ROOT / name
        summary[name] = evaluate_folder(folder)

    output_path = ARTIFACT_ROOT / "evaluation_results.json"
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    failures = []
    for group, rows in summary.items():
        for row in rows:
            status = "PASS" if row["passes_expectation"] else "FAIL"
            print(f"[{status}] {group}: {Path(row['file']).name} -> {row['verdict']} ({row['processing_time_ms']}ms)")
            if not row["passes_expectation"]:
                failures.append(row)

    print(f"\nSaved detailed results to {output_path}")
    if failures:
        raise SystemExit(f"{len(failures)} artifact checks failed")


if __name__ == "__main__":
    main()
