from pathlib import Path
from time import perf_counter
from concurrent.futures import ThreadPoolExecutor

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
HOSTED_EXECUTOR = ThreadPoolExecutor(max_workers=3)


def _safe_model_call(label: str, fn, *args):
    try:
        return fn(*args)
    except Exception as exc:
        logger.exception(
            "hosted inference call failed",
            extra={"extra_payload": {"model_role": label, "error": str(exc)}},
        )
        return {"status": "error", "reason": str(exc)}


def _normalize_field_value(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned or cleaned.lower() in {"not detected", "unknown", "n/a", "null"}:
        return None
    return cleaned


def _merge_extracted_fields(primary, fallback: dict | None):
    if not isinstance(fallback, dict):
        return primary
    data = primary.model_dump()
    for key, value in fallback.items():
        if key not in data:
            continue
        if _normalize_field_value(data[key]) is None and _normalize_field_value(value) is not None:
            data[key] = str(value).strip()
    return type(primary)(**data)


def _has_structured_fields(extracted_fields) -> bool:
    values = extracted_fields.model_dump()
    present = sum(1 for value in values.values() if _normalize_field_value(value) is not None)
    return present >= 4 and _normalize_field_value(values.get("reference")) is not None


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
        stage_callback("reviewing_changes")
    should_skip_hosted = mime_type == "application/pdf" or "edited_overlay_signal" in quality_flags
    if should_skip_hosted:
        reasoner_response = {"status": "not_applicable"}
        tamper_response = {"status": "not_applicable"}
        synthetic_response = {"status": "not_applicable"}
    else:
        reasoner_future = HOSTED_EXECUTOR.submit(
            _safe_model_call, "artifact_reasoner", call_artifact_reasoner, file_path, artifact_type
        )
        tamper_future = HOSTED_EXECUTOR.submit(_safe_model_call, "tamper_detector", call_tamper_detector, file_path)
        synthetic_future = HOSTED_EXECUTOR.submit(
            _safe_model_call, "synthetic_artifact_detector", call_synthetic_artifact_detector, file_path, artifact_type
        )
        reasoner_response = reasoner_future.result()
        tamper_response = tamper_future.result()
        synthetic_response = synthetic_future.result()
    extracted_fields = _merge_extracted_fields(extracted_fields, reasoner_response.get("extracted_fields"))
    suspicious_signals = reasoner_response.get("suspicious_signals")
    has_reasoner_suspicion = False
    if isinstance(suspicious_signals, list):
        normalized_signals = [str(signal).strip() for signal in suspicious_signals if str(signal).strip()]
        if normalized_signals:
            has_reasoner_suspicion = True
    has_confident_fields = _has_structured_fields(extracted_fields)
    if stage_callback:
        stage_callback("checking_details")
    rule_hits, reasons = run_rules(artifact_type, raw_text, extracted_fields, quality_flags)
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
    if (
        isinstance(synthetic_probability, (int, float))
        and synthetic_probability >= 0.85
        and (has_reasoner_suspicion or not has_confident_fields)
    ):
        reasons.append("One of our image checks suggests this payment document may not be an original banking artifact.")
        quality_flags.append("synthetic_artifact_signal")
    tamper_probability = tamper_response.get("tamper_probability")
    if (
        isinstance(tamper_probability, (int, float))
        and tamper_probability >= 0.85
        and (has_reasoner_suspicion or not has_confident_fields)
    ):
        reasons.append("One image-integrity check raised a caution flag on this payment document.")
        quality_flags.append("tamper_signal")
    if isinstance(suspicious_signals, list):
        normalized_signals = [str(signal).strip() for signal in suspicious_signals if str(signal).strip()]
        if normalized_signals:
            reasons.extend(normalized_signals)
            quality_flags.append("reasoner_suspicious_signal")
    trust_cues = reasoner_response.get("trust_cues")
    if isinstance(trust_cues, list) and not reasons:
        reasons.extend(str(cue).strip() for cue in trust_cues[:2] if str(cue).strip())
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
