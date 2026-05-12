from fastapi.testclient import TestClient

from app.main import app


def test_get_wallet_route_returns_balance(monkeypatch):
    client = TestClient(app)

    class DummyWallet:
        balance = 7
        status = "active"
        last_payment_reference = "ref_123"

    monkeypatch.setattr(
        "app.api.routes.dev.get_or_create_user",
        lambda db, whatsapp_id: type("User", (), {"id": 1})(),
    )
    monkeypatch.setattr("app.api.routes.dev.get_or_create_wallet", lambda db, user_id: DummyWallet())

    response = client.get("/api/dev/wallet/dev-user")

    assert response.status_code == 200
    assert response.json()["balance"] == 7


def test_recharge_wallet_route_returns_checkout(monkeypatch):
    client = TestClient(app)

    class DummyWallet:
        balance = 0
        status = "active"
        last_payment_reference = None

    monkeypatch.setattr(
        "app.api.routes.dev.get_or_create_user",
        lambda db, whatsapp_id: type("User", (), {"id": 1})(),
    )
    monkeypatch.setattr("app.api.routes.dev.get_or_create_wallet", lambda db, user_id: DummyWallet())
    async def fake_initiate_recharge_checkout(db, user, customer_email, amount_kobo, credits_to_add):
        return (
            type("Txn", (), {"transaction_ref": "ref_123", "status": "pending"})(),
            {"data": {"checkout_url": "https://checkout.example.com"}},
        )

    monkeypatch.setattr("app.api.routes.dev.initiate_recharge_checkout", fake_initiate_recharge_checkout)

    response = client.post(
        "/api/dev/wallet/recharge",
        data={
            "whatsapp_id": "dev-user",
            "customer_email": "dev@example.com",
            "amount_kobo": 500000,
            "credits_to_add": 20,
        },
    )

    assert response.status_code == 200
    assert response.json()["balance"] == 0
    assert response.json()["transaction_ref"] == "ref_123"
    assert response.json()["status"] == "pending"
    assert response.json()["checkout"]["data"]["checkout_url"] == "https://checkout.example.com"
