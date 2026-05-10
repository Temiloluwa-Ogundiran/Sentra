from pathlib import Path

from app.core.config import settings
from app.integrations.sagemaker import SageMakerClient


def call_artifact_reasoner_endpoint(file_path: Path, artifact_type: str) -> dict:
    if not settings.model_artifact_reasoner_endpoint:
        return {"status": "skipped", "reason": "missing_endpoint"}
    client = SageMakerClient()
    return client.invoke_json(
        settings.model_artifact_reasoner_endpoint,
        {"artifact_type": artifact_type, "file_name": file_path.name},
    )


def call_tamper_detector_endpoint(file_path: Path) -> dict:
    if not settings.model_tamper_detector_endpoint:
        return {"status": "skipped", "reason": "missing_endpoint"}
    client = SageMakerClient()
    return client.invoke_json(
        settings.model_tamper_detector_endpoint,
        {"file_name": file_path.name},
    )


def call_synthetic_artifact_detector_endpoint(file_path: Path, artifact_type: str) -> dict:
    if not settings.model_synthetic_artifact_detector_endpoint:
        return {"status": "skipped", "reason": "missing_endpoint"}
    client = SageMakerClient()
    return client.invoke_json(
        settings.model_synthetic_artifact_detector_endpoint,
        {"artifact_type": artifact_type, "file_name": file_path.name},
    )
