from app.core.config import settings


def test_hosted_config_fields_exist():
    assert hasattr(settings, "hosted_artifact_reasoner_url")
    assert hasattr(settings, "hosted_tamper_detector_url")
    assert hasattr(settings, "hosted_synthetic_artifact_detector_url")
