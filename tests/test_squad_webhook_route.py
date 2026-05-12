import hmac
import json
from hashlib import sha512

from fastapi.testclient import TestClient

from app.main import app


def test_squad_webhook_route_returns_applied(monkeypatch):
    client = TestClient(app)
    payload = {"Event": "charge_successful", "TransactionRef": "ref_123", "Body": {"transaction_ref": "ref_123"}}
    raw_body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(b"sandbox_sk_testsecret", raw_body, sha512).hexdigest().upper()

    async def fake_process(db, raw_body, payload, header_signature, secret_key):
        return 200, {"status": "applied", "transaction_ref": "ref_123"}

    monkeypatch.setattr("app.api.routes.webhooks.process_squad_webhook", fake_process)
    monkeypatch.setattr("app.api.routes.webhooks.settings.squad_secret_key", "sandbox_sk_testsecret")

    response = client.post(
        "/api/webhooks/squad",
        json=payload,
        headers={"x-squad-encrypted-body": signature},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "applied"
