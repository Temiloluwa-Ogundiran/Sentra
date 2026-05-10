from pathlib import Path
from time import perf_counter

from app.inference.annotate import annotate_artifact
from app.inference.artifact_classifier import classify_artifact
from app.inference.fusion import fuse_result
from app.inference.ocr import run_ocr
from app.inference.quality import assess_quality
from app.inference.rules import run_rules
from app.inference.sagemaker_runtime import (
    call_artifact_reasoner_endpoint,
    call_synthetic_artifact_detector_endpoint,
    call_tamper_detector_endpoint,
)
from app.schemas.common import CanonicalResult


def run_pipeline(request_id: int, file_path: Path, mime_type: str, expected_amount: str | None = None) -> tuple[CanonicalResult, dict]:
    started = perf_counter()
    artifact_type = classify_artifact(file_path, mime_type)
    quality_flags = assess_quality(file_path)
    raw_text, extracted_fields = run_ocr(file_path)
    rule_hits, reasons = run_rules(artifact_type, raw_text, quality_flags)
    reasoner_response = call_artifact_reasoner_endpoint(file_path, artifact_type)
    tamper_response = call_tamper_detector_endpoint(file_path)
    synthetic_response = call_synthetic_artifact_detector_endpoint(file_path, artifact_type)
    if reasoner_response.get("status") == "skipped":
        reasons.append("Hosted artifact reasoning was not configured.")
    if tamper_response.get("status") == "skipped":
        reasons.append("Hosted tamper analysis was not configured.")
    if synthetic_response.get("status") == "skipped":
        reasons.append("Hosted AI-generated artifact detection was not configured.")
    synthetic_probability = synthetic_response.get("synthetic_probability")
    if isinstance(synthetic_probability, (int, float)) and synthetic_probability >= 0.7:
        reasons.append("This proof contains signals consistent with AI-generated or synthetic content.")
        quality_flags.append("synthetic_artifact_signal")
    annotated = annotate_artifact(file_path, artifact_type, reasons, request_id)
    processing_time_ms = int((perf_counter() - started) * 1000)
    result = fuse_result(
        request_id=request_id,
        artifact_type=artifact_type,
        extracted_fields=extracted_fields,
        reasons=reasons,
        quality_flags=quality_flags,
        processing_time_ms=processing_time_ms,
        expected_amount=expected_amount,
        annotated_artifact_path=str(annotated),
    )
    debug = {
        "raw_text": raw_text,
        "rule_hits": rule_hits,
        "model_scores": {
            "artifact_reasoner": reasoner_response,
            "tamper_detector": tamper_response,
            "synthetic_artifact_detector": synthetic_response,
        },
    }
    return result, debug
