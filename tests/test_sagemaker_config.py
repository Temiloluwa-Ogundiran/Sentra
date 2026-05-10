from app.core.config import settings


def test_sagemaker_config_fields_exist():
    assert hasattr(settings, "bedrock_artifact_reasoner_model_id")
    assert hasattr(settings, "model_tamper_detector_endpoint")
    assert hasattr(settings, "model_synthetic_artifact_detector_endpoint")
