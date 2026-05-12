from pathlib import Path
from time import perf_counter

from app.core.logging import get_logger
from app.inference.annotate import annotate_artifact
from app.inference.artifact_classifier import classify_artifact
from app.inference.fusion import fuse_result
from app.inference.hosted_runtime import (
    call_artifact_reasoner,
    call_synthetic_artifact_detector,
    call_tamper_detector,
)
from app.inference.ocr import run_ocr
from app.inference.quality import assess_quality
from app.inference.rules import run_rules
from app.schemas.common import CanonicalResult

logger = get_logger(__name__)


def _safe_model_call(label: str, fn, *args):
    try:
        return fn(*args)
    except Exception as exc:
        logger.exception(
            "hosted inference call failed",
            extra={"extra_payload": {"model_role": label, "error": str(exc)}},
        )
        return {"status": "error", "reason": str(exc)}


def run_pipeline(
    request_id: int,
    file_path: Path,
    mime_type: str,
    expected_amount: str | None = None,
    stage_callback=None,
) -> tuple[CanonicalResult, dict]:
    started = perf_counter()
    if stage_callback:
        stage_callback("preparing")
    artifact_type = classify_artifact(file_path, mime_type)
    quality_flags = assess_quality(file_path)
    if stage_callback:
        stage_callback("reading_proof")
    raw_text, extracted_fields = run_ocr(file_path)
    if stage_callback:
        stage_callback("checking_details")
    rule_hits, reasons = run_rules(artifact_type, raw_text, quality_flags)
    if stage_callback:
        stage_callback("reviewing_changes")
    reasoner_response = _safe_model_call("artifact_reasoner", call_artifact_reasoner, file_path, artifact_type)
    tamper_response = _safe_model_call("tamper_detector", call_tamper_detector, file_path)
    synthetic_response = _safe_model_call(
        "synthetic_artifact_detector", call_synthetic_artifact_detector, file_path, artifact_type
    )
    if reasoner_response.get("status") == "skipped":
        reasons.append("Hosted artifact reasoning was not configured.")
    if reasoner_response.get("status") == "error":
        reasons.append("Artifact reasoning is temporarily unavailable, so this result uses fallback checks.")
    if tamper_response.get("status") == "skipped":
        reasons.append("Hosted tamper analysis was not configured.")
    if tamper_response.get("status") == "error":
        reasons.append("Tamper analysis is temporarily unavailable, so this result uses fallback checks.")
    if synthetic_response.get("status") == "skipped":
        reasons.append("Hosted AI-generated artifact detection was not configured.")
    if synthetic_response.get("status") == "error":
        reasons.append("Synthetic-artifact detection is temporarily unavailable, so this result uses fallback checks.")
    synthetic_probability = synthetic_response.get("synthetic_probability")
    if isinstance(synthetic_probability, (int, float)) and synthetic_probability >= 0.7:
        reasons.append("This proof contains signals consistent with AI-generated or synthetic content.")
        quality_flags.append("synthetic_artifact_signal")
    tamper_probability = tamper_response.get("tamper_probability")
    if isinstance(tamper_probability, (int, float)) and tamper_probability >= 0.7:
        reasons.append("This proof contains strong signals of manipulation or fraudulent editing.")
        quality_flags.append("tamper_signal")
    suspicious_signals = reasoner_response.get("suspicious_signals")
    if isinstance(suspicious_signals, list):
        reasons.extend(str(signal).strip() for signal in suspicious_signals if str(signal).strip())
    trust_cues = reasoner_response.get("trust_cues")
    if isinstance(trust_cues, list):
        reasons.extend(str(cue).strip() for cue in trust_cues if str(cue).strip())
    reasoner_summary = reasoner_response.get("summary") or reasoner_response.get("raw_text")
    if isinstance(reasoner_summary, str) and reasoner_summary.strip():
        reasons.append(reasoner_summary.strip())
    if stage_callback:
        stage_callback("finalizing")
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
