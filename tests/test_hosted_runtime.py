from app.inference.hosted_runtime import _extract_probability, _recover_reasoner_response


def test_recover_reasoner_response_salvages_truncated_json_fields():
    response = {
        "raw_text": """```json
{
  "artifact_type_guess": "Bank Transfer Confirmation",
  "extracted_fields": {
    "amount": 4000,
    "currency": "NGN",
    "date": "2026-05-11",
    "time": "07:51 AM",
    "reference": "TRF|2MPTkgmd0|2053729666401218560",
    "provider": "Moniepoint",
    "recipient_label": "Cleva Tech - Temiloluwa Ogundiran"
  },
  "suspicious_signals": [],
  "trust_cues": [
    "Successful transaction status"
"""
    }

    recovered = _recover_reasoner_response(response)

    assert recovered["artifact_type_guess"] == "Bank Transfer Confirmation"
    assert recovered["extracted_fields"]["amount"] == "4000"
    assert recovered["extracted_fields"]["reference"] == "TRF|2MPTkgmd0|2053729666401218560"
    assert recovered["suspicious_signals"] == []


def test_extract_probability_ignores_negative_labels():
    predictions = [
        {"label": "non_fraudulent", "score": 0.999},
        {"label": "fraud_crop_replace", "score": 0.2},
    ]

    probability = _extract_probability(
        predictions,
        ("fraud", "crop", "replace"),
        ("non_fraud", "non-fraud"),
    )

    assert probability == 0.2
