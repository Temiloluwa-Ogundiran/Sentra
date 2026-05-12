from pathlib import Path
import re

from app.core.config import settings
from app.inference.visual_payload import prepare_visual_payload
from app.integrations.modal import ModalClient


def _extract_string_field(raw_text: str, key: str) -> str | None:
    patterns = [
        rf'"{re.escape(key)}"\s*:\s*"([^"]+)"',
        rf'"{re.escape(key)}"\s*:\s*([0-9][0-9.,]*)',
    ]
    for pattern in patterns:
        match = re.search(pattern, raw_text)
        if match:
            return match.group(1).strip().rstrip(",")
    return None


def _recover_reasoner_response(response: dict) -> dict:
    raw_text = response.get("raw_text")
    if not isinstance(raw_text, str):
        return response

    extracted_fields = response.get("extracted_fields")
    if not isinstance(extracted_fields, dict):
        extracted_fields = {}

    recovered_fields = {
        key: value
        for key in ("amount", "currency", "date", "time", "reference", "provider", "recipient_label")
        if (value := _extract_string_field(raw_text, key)) is not None
    }
    if recovered_fields and not extracted_fields:
        response["extracted_fields"] = recovered_fields

    artifact_type_guess = response.get("artifact_type_guess")
    if not artifact_type_guess:
        recovered_artifact_type = _extract_string_field(raw_text, "artifact_type_guess")
        if recovered_artifact_type:
            response["artifact_type_guess"] = recovered_artifact_type

    if "suspicious_signals" not in response:
        if re.search(r'"suspicious_signals"\s*:\s*\[\s*\]', raw_text):
            response["suspicious_signals"] = []
        else:
            match = re.search(r'"suspicious_signals"\s*:\s*\[(.*?)\]', raw_text, re.DOTALL)
            if match:
                signals = re.findall(r'"([^"]+)"', match.group(1))
                response["suspicious_signals"] = [signal.strip() for signal in signals if signal.strip()]

    if "trust_cues" not in response:
        match = re.search(r'"trust_cues"\s*:\s*\[(.*?)\]', raw_text, re.DOTALL)
        if match:
            cues = re.findall(r'"([^"]+)"', match.group(1))
            response["trust_cues"] = [cue.strip() for cue in cues if cue.strip()]

    return response


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
        "Do not list ordinary layout details as suspicious_signals. "
        "Return valid JSON only. Do not include markdown fences or comments."
    )
    client = ModalClient()
    response = client.invoke_json(
        settings.hosted_artifact_reasoner_url,
        {
            "image_base64": image_base64,
            "image_format": image_format,
            "artifact_type": artifact_type,
            "prompt": prompt,
        },
    )
    return _recover_reasoner_response(response)


def _extract_probability(
    predictions: list[dict],
    positive_terms: tuple[str, ...],
    negative_terms: tuple[str, ...] = (),
) -> float | None:
    probabilities: list[float] = []
    for item in predictions:
        label = str(item.get("label", "")).lower()
        score = item.get("score")
        if any(term in label for term in negative_terms):
            continue
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
        ("non_fraud", "non-fraud", "genuine", "clean", "authentic"),
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
        ("human", "real", "authentic"),
    )
    response["synthetic_probability"] = synthetic_probability
    return response
