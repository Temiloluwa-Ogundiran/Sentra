from pydantic import BaseModel


class ExtractedFields(BaseModel):
    amount: str | None = None
    currency: str | None = None
    date: str | None = None
    time: str | None = None
    reference: str | None = None
    provider: str | None = None
    recipient_label: str | None = None


class CanonicalResult(BaseModel):
    request_id: int
    artifact_type: str
    verdict: str
    recommended_action: str
    extracted_fields: ExtractedFields
    reasons: list[str]
    quality_flags: list[str]
    annotated_artifact_path: str | None = None
    processing_time_ms: int
    expected_amount: str | None = None
