from app.services.readiness import get_readiness_status


def test_readiness_shape():
    status = get_readiness_status()
    assert "status" in status
    assert "checks" in status
