from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app


def test_dev_upload_endpoint_accepts_file(monkeypatch):
    client = TestClient(app)

    async def fake_create_request(*args, **kwargs):
        return 123

    monkeypatch.setattr("app.api.routes.dev.create_request_from_upload", fake_create_request)
    monkeypatch.setattr("app.api.routes.dev.worker_queue.enqueue", lambda request_id: None)

    response = client.post(
        "/api/dev/upload",
        files={"file": ("proof.png", b"fake-image-bytes", "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["request_id"] == 123
