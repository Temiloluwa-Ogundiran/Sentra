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
        lambda artifact_type, raw_text, extracted_fields, quality_flags: (["reference.present"], ["Reference detected."]),
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
    assert "Provider layout looks coherent" not in result.reasons
    assert "One image-integrity check raised a caution flag on this proof." in result.reasons
    assert debug["model_scores"]["artifact_reasoner"]["summary"] == "Likely edited amount field."


def test_run_pipeline_degrades_gracefully_when_reasoner_endpoint_fails(monkeypatch, tmp_path):
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
        lambda artifact_type, raw_text, extracted_fields, quality_flags: (["reference.present"], ["Reference detected."]),
    )

    def failing_reasoner(file_path, artifact_type):
        raise RuntimeError("404 hosted reasoner")

    monkeypatch.setattr("app.inference.pipeline.call_artifact_reasoner", failing_reasoner)
    monkeypatch.setattr(
        "app.inference.pipeline.call_tamper_detector",
        lambda file_path: {"status": "skipped", "reason": "missing_url"},
    )
    monkeypatch.setattr(
        "app.inference.pipeline.call_synthetic_artifact_detector",
        lambda file_path, artifact_type: {"status": "skipped", "reason": "missing_url"},
    )
    monkeypatch.setattr(
        "app.inference.pipeline.annotate_artifact",
        lambda file_path, artifact_type, reasons, request_id: tmp_path / "annotated.png",
    )

    result, debug = run_pipeline(
        request_id=77,
        file_path=sample,
        mime_type="image/png",
        expected_amount="25000",
    )

    assert result.request_id == 77
    assert result.verdict in {"Review", "High-confidence pattern match", "Suspicious"}
    assert any("unavailable" in reason.lower() or "not configured" in reason.lower() for reason in result.reasons)
    assert debug["model_scores"]["artifact_reasoner"]["status"] == "error"


def test_run_pipeline_merges_reasoner_fields_when_ocr_misses(monkeypatch, tmp_path):
    sample = tmp_path / "proof.png"
    Image.new("RGB", (900, 1200), color="white").save(sample)

    monkeypatch.setattr("app.inference.pipeline.classify_artifact", lambda file_path, mime_type: "bank_alert_screenshot")
    monkeypatch.setattr("app.inference.pipeline.assess_quality", lambda file_path: [])
    monkeypatch.setattr(
        "app.inference.pipeline.run_ocr",
        lambda file_path: (
            "",
            __import__("app.schemas.common", fromlist=["ExtractedFields"]).ExtractedFields(),
        ),
    )
    monkeypatch.setattr(
        "app.inference.pipeline.run_rules",
        lambda artifact_type, raw_text, extracted_fields, quality_flags: (
            [],
            [] if extracted_fields.reference else ["A clear transaction reference was not detected."],
        ),
    )
    monkeypatch.setattr(
        "app.inference.pipeline.call_artifact_reasoner",
        lambda file_path, artifact_type: {
            "artifact_type_guess": "bank_alert_screenshot",
            "extracted_fields": {
                "amount": "4000.00",
                "currency": "NGN",
                "date": "2026-05-11",
                "time": "7:51 AM",
                "reference": "TRF|2MPTkgmd0|2053729666401218560",
                "provider": "MONIEPOINT",
                "recipient_label": "Cleva Tech - Temiloluwa Ogundiran | 1364143808",
            },
            "suspicious_signals": [],
            "trust_cues": ["Moniepoint logo and branding"],
            "summary": "Clean banking alert layout.",
        },
    )
    monkeypatch.setattr(
        "app.inference.pipeline.call_tamper_detector",
        lambda file_path: {"tamper_probability": 0.2, "predictions": [{"label": "non_fraudulent", "score": 0.8}]},
    )
    monkeypatch.setattr(
        "app.inference.pipeline.call_synthetic_artifact_detector",
        lambda file_path, artifact_type: {"synthetic_probability": 0.1, "predictions": []},
    )
    monkeypatch.setattr(
        "app.inference.pipeline.annotate_artifact",
        lambda file_path, artifact_type, reasons, request_id: tmp_path / "annotated.png",
    )

    result, _ = run_pipeline(
        request_id=88,
        file_path=sample,
        mime_type="image/png",
    )

    assert result.extracted_fields.amount == "4000.00"
    assert result.extracted_fields.reference == "TRF|2MPTkgmd0|2053729666401218560"
    assert result.verdict == "High-confidence pattern match"


def test_run_pipeline_skips_hosted_calls_for_pdf(monkeypatch, tmp_path):
    import fitz

    pdf_path = tmp_path / "receipt.pdf"
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((50, 80), "Payment Reference\nABC123456\nAmount\n₦ 500.00")
    document.save(pdf_path)
    document.close()

    monkeypatch.setattr("app.inference.pipeline.classify_artifact", lambda file_path, mime_type: "receipt_pdf_render")
    monkeypatch.setattr("app.inference.pipeline.assess_quality", lambda file_path: [])
    monkeypatch.setattr(
        "app.inference.pipeline.run_ocr",
        lambda file_path: (
            "Payment Reference ABC123456 Amount 500.00",
            __import__("app.schemas.common", fromlist=["ExtractedFields"]).ExtractedFields(
                amount="500.00",
                currency="NGN",
                reference="ABC123456",
            ),
        ),
    )
    monkeypatch.setattr(
        "app.inference.pipeline.run_rules",
        lambda artifact_type, raw_text, extracted_fields, quality_flags: ([], []),
    )
    monkeypatch.setattr(
        "app.inference.pipeline.call_artifact_reasoner",
        lambda *args: (_ for _ in ()).throw(AssertionError("artifact reasoner should not run for pdf")),
    )
    monkeypatch.setattr(
        "app.inference.pipeline.call_tamper_detector",
        lambda *args: (_ for _ in ()).throw(AssertionError("tamper should not run for pdf")),
    )
    monkeypatch.setattr(
        "app.inference.pipeline.call_synthetic_artifact_detector",
        lambda *args: (_ for _ in ()).throw(AssertionError("synthetic should not run for pdf")),
    )
    monkeypatch.setattr(
        "app.inference.pipeline.annotate_artifact",
        lambda file_path, artifact_type, reasons, request_id: tmp_path / "annotated.png",
    )

    result, debug = run_pipeline(
        request_id=90,
        file_path=pdf_path,
        mime_type="application/pdf",
    )

    assert result.verdict == "High-confidence pattern match"
    assert debug["model_scores"]["artifact_reasoner"]["status"] == "not_applicable"
