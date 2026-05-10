import os

import pytest

from app.integrations.sagemaker import SageMakerClient


@pytest.mark.skipif(
    not (
        os.getenv("AWS_ACCESS_KEY_ID")
        and os.getenv("AWS_SECRET_ACCESS_KEY")
        and os.getenv("MODEL_ARTIFACT_REASONER_ENDPOINT")
    ),
    reason="Live SageMaker credentials/endpoints not configured",
)
def test_live_sagemaker_connection():
    client = SageMakerClient()
    response = client.invoke_json(os.environ["MODEL_ARTIFACT_REASONER_ENDPOINT"], {"ping": True})
    assert response is not None
