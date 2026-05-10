import os

import pytest

from app.integrations.bedrock import BedrockClient
from app.integrations.sagemaker import SageMakerClient


@pytest.mark.skipif(
    not (
        os.getenv("AWS_ACCESS_KEY_ID")
        and os.getenv("AWS_SECRET_ACCESS_KEY")
        and os.getenv("MODEL_TAMPER_DETECTOR_ENDPOINT")
    ),
    reason="Live SageMaker credentials/endpoints not configured",
)
def test_live_sagemaker_connection():
    client = SageMakerClient()
    response = client.invoke_json(os.environ["MODEL_TAMPER_DETECTOR_ENDPOINT"], {"ping": True})
    assert response is not None


@pytest.mark.skipif(
    not (
        os.getenv("AWS_ACCESS_KEY_ID")
        and os.getenv("AWS_SECRET_ACCESS_KEY")
        and os.getenv("BEDROCK_ARTIFACT_REASONER_MODEL_ID")
    ),
    reason="Live Bedrock model configuration not present",
)
def test_live_bedrock_client_instantiates():
    client = BedrockClient()
    assert client.runtime is not None
