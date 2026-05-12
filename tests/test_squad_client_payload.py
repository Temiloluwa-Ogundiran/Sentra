import json

import pytest

from app.integrations.squad import SquadClient


class _DummyResponse:
    def __init__(self, status_code: int = 200, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {"data": {"checkout_url": "https://checkout.example/pay"}}
        self.text = json.dumps(self._payload)
        self.request = None

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx

            raise httpx.HTTPStatusError("bad request", request=self.request, response=self)

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_create_credit_checkout_omits_callback_url_when_unset(monkeypatch):
    sent_json: dict = {}

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json=None, headers=None):
            sent_json.update(json or {})
            return _DummyResponse()

    monkeypatch.setattr("app.integrations.squad.httpx.AsyncClient", DummyClient)
    monkeypatch.setattr("app.integrations.squad.settings.squad_callback_url", "")

    payload = await SquadClient().create_credit_checkout(
        customer_email="temi@example.com",
        amount_kobo=500000,
        credits_to_add=20,
        user_id=2,
        transaction_ref="sentra_test_ref",
    )

    assert payload["data"]["checkout_url"] == "https://checkout.example/pay"
    assert "callback_url" not in sent_json

