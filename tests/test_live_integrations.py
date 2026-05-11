import os

import pytest

from app.integrations.modal import ModalClient


@pytest.mark.skipif(
    not (
        os.getenv("HOSTED_TAMPER_DETECTOR_URL")
    ),
    reason="Live hosted detector URL not configured",
)
def test_live_hosted_detector_connection():
    client = ModalClient()
    response = client.invoke_json(os.environ["HOSTED_TAMPER_DETECTOR_URL"], {"ping": True})
    assert response is not None


@pytest.mark.skipif(
    not (
        os.getenv("HOSTED_ARTIFACT_REASONER_URL")
    ),
    reason="Live hosted reasoner URL not present",
)
def test_live_hosted_reasoner_connection():
    client = ModalClient()
    response = client.invoke_json(
        os.environ["HOSTED_ARTIFACT_REASONER_URL"],
        {"ping": True},
    )
    assert response is not None
