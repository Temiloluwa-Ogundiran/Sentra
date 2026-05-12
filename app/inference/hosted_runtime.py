from pathlib import Path

from app.core.config import settings
from app.inference.visual_payload import prepare_visual_payload
from app.integrations.modal import ModalClient


def call_artifact_reasoner(file_path: Path, artifact_type: str) -> dict:
    if not settings.hosted_artifact_reasoner_url:
        return {"status": "skipped", "reason": "missing_url"}

    image_base64, _, image_format = prepare_visual_payload(file_path)
    prompt = (
        "You are analyzing a payment-proof artifact for fraud risk. "
        f"Artifact type guess: {artifact_type}. "
        "Return concise JSON with keys: artifact_type_guess, extracted_fields, suspicious_signals, trust_cues, summary. "
        "For extracted_fields, return: amount, currency, date, time, reference, provider, recipient_label. "
        "Only list suspicious_signals when there is concrete visual evidence of editing, inconsistency, or fabrication. "
        "Do not list ordinary layout details as suspicious_signals."
    )
    client = ModalClient()
    return client.invoke_json(
        settings.hosted_artifact_reasoner_url,
        {
            "image_base64": image_base64,
            "image_format": image_format,
            "artifact_type": artifact_type,
            "prompt": prompt,
        },
    )


def _extract_probability(predictions: list[dict], positive_terms: tuple[str, ...]) -> float | None:
    probabilities: list[float] = []
    for item in predictions:
        label = str(item.get("label", "")).lower()
        score = item.get("score")
        if isinstance(score, (int, float)) and any(term in label for term in positive_terms):
            probabilities.append(float(score))
    return max(probabilities) if probabilities else None


def call_tamper_detector(file_path: Path) -> dict:
    if not settings.hosted_tamper_detector_url:
        return {"status": "skipped", "reason": "missing_url"}

    image_base64, _, _ = prepare_visual_payload(file_path)
    client = ModalClient()
    response = client.invoke_json(
        settings.hosted_tamper_detector_url,
        {"image_base64": image_base64},
    )
    predictions = response.get("predictions", [])
    tamper_probability = _extract_probability(
        predictions,
        ("fraud", "forg", "manip", "tamper", "fake", "inpaint", "crop", "replace"),
    )
    response["tamper_probability"] = tamper_probability
    return response


def call_synthetic_artifact_detector(file_path: Path, artifact_type: str) -> dict:
    if not settings.hosted_synthetic_artifact_detector_url:
        return {"status": "skipped", "reason": "missing_url"}

    image_base64, _, _ = prepare_visual_payload(file_path)
    client = ModalClient()
    response = client.invoke_json(
        settings.hosted_synthetic_artifact_detector_url,
        {"image_base64": image_base64, "artifact_type": artifact_type},
    )
    predictions = response.get("predictions", [])
    synthetic_probability = _extract_probability(
        predictions,
        ("synthetic", "ai", "generated", "fake"),
    )
    response["synthetic_probability"] = synthetic_probability
    return response
