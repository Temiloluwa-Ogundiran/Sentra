from pathlib import Path

from PIL import Image

from app.inference.pipeline import run_pipeline


def test_run_pipeline_combines_hosted_signals(monkeypatch, tmp_path):
    sample = tmp_path / "proof.png"
    Image.new("RGB", (900, 1200), color="white").save(sample)

    monkeypatch.setattr("app.inference.pipeline.classify_artifact", lambda file_path, mime_type: "bank_alert_screenshot")
    monkeypatch.setattr("app.inference.pipeline.assess_quality", lambda file_path: [])
    monkeypatch.setattr(
        "app.inference.pipeline.run_ocr",
        lambda file_path: (
            "Amount NGN 25000\nRef TX123456789\nRecipient SENTRA STORE",
            __import__("app.schemas.common", fromlist=["ExtractedFields"]).ExtractedFields(
                amount="25000",
                currency="NGN",
                reference="TX123456789",
                recipient_label="SENTRA STORE",
            ),
        ),
    )
    monkeypatch.setattr(
        "app.inference.pipeline.run_rules",
        lambda artifact_type, raw_text, quality_flags: (["reference.present"], ["Reference detected."]),
    )
    monkeypatch.setattr(
        "app.inference.pipeline.call_artifact_reasoner",
        lambda file_path, artifact_type: {
            "artifact_type_guess": "bank_alert_screenshot",
            "suspicious_signals": ["Amount region edited"],
            "trust_cues": ["Provider layout looks coherent"],
            "summary": "Likely edited amount field.",
        },
    )
    monkeypatch.setattr(
        "app.inference.pipeline.call_tamper_detector",
        lambda file_path: {"tamper_probability": 0.91, "predictions": [{"label": "fraud_crop_replace", "score": 0.91}]},
    )
    monkeypatch.setattr(
        "app.inference.pipeline.call_synthetic_artifact_detector",
        lambda file_path, artifact_type: {
            "synthetic_probability": 0.12,
            "predictions": [{"label": "by human", "score": 0.88}],
        },
    )
    monkeypatch.setattr(
        "app.inference.pipeline.annotate_artifact",
        lambda file_path, artifact_type, reasons, request_id: tmp_path / "annotated.png",
    )

    result, debug = run_pipeline(
        request_id=42,
        file_path=sample,
        mime_type="image/png",
        expected_amount="25000",
    )

    assert result.request_id == 42
    assert result.extracted_fields.amount == "25000"
    assert result.annotated_artifact_path == str(tmp_path / "annotated.png")
    assert "Amount region edited" in result.reasons
    assert "Provider layout looks coherent" in result.reasons
    assert "This proof contains strong signals of manipulation or fraudulent editing." in result.reasons
    assert debug["model_scores"]["artifact_reasoner"]["summary"] == "Likely edited amount field."
