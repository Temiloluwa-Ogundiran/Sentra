from fastapi.testclient import TestClient

from app.main import app


def test_gowa_webhook_replies_to_text_only_message(monkeypatch):
    client = TestClient(app)
    sent_messages: list[tuple[str, str]] = []
    sent_typing: list[str] = []

    class Decision:
        action = "reply_help"
        reply_text = (
            "Hi — Sentra checks one payment document screenshot or PDF at a time. "
            "Send a JPG, PNG, or PDF payment document."
        )
        start_verification = False

    async def fake_decide_inbound_action(db, payload):
        return Decision()

    async def fake_send_text(self, to: str, text: str) -> None:
        sent_messages.append((to, text))

    async def fake_send_chat_presence(self, to: str, presence: str = "composing", media_type: str = "text") -> None:
        sent_typing.append(to)

    monkeypatch.setattr("app.api.routes.webhooks.decide_inbound_action", fake_decide_inbound_action)
    monkeypatch.setattr("app.api.routes.webhooks.GowaClient.send_text", fake_send_text)
    monkeypatch.setattr("app.api.routes.webhooks.GowaClient.send_chat_presence", fake_send_chat_presence)

    response = client.post(
        "/api/webhooks/gowa",
        json={
            "event": "message",
            "payload": {
                "from": "2349025283155@s.whatsapp.net",
                "body": "Hi",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["request_id"] is None
    assert sent_typing == ["2349025283155@s.whatsapp.net"]
    assert sent_messages == [
        (
            "2349025283155@s.whatsapp.net",
            "Hi — Sentra checks one payment document screenshot or PDF at a time. Send a JPG, PNG, or PDF payment document.",
        )
    ]


def test_gowa_webhook_replies_when_credits_are_exhausted(monkeypatch):
    client = TestClient(app)
    sent_messages: list[tuple[str, str]] = []
    sent_typing: list[str] = []

    class Decision:
        action = "reply_recharge_required"
        reply_text = (
            "Your Sentra verification credits are exhausted. "
            "Recharge your credits before submitting another payment document."
        )
        start_verification = True

    async def fake_decide_inbound_action(db, payload):
        return Decision()

    async def fake_create_request_from_gowa_event(db, payload):
        from app.services.wallets import InsufficientCreditsError

        raise InsufficientCreditsError("Insufficient verification credits.")

    async def fake_send_text(self, to: str, text: str) -> None:
        sent_messages.append((to, text))

    async def fake_send_chat_presence(self, to: str, presence: str = "composing", media_type: str = "text") -> None:
        sent_typing.append(to)

    monkeypatch.setattr("app.api.routes.webhooks.decide_inbound_action", fake_decide_inbound_action)
    monkeypatch.setattr("app.api.routes.webhooks.create_request_from_gowa_event", fake_create_request_from_gowa_event)
    monkeypatch.setattr("app.api.routes.webhooks.GowaClient.send_text", fake_send_text)
    monkeypatch.setattr("app.api.routes.webhooks.GowaClient.send_chat_presence", fake_send_chat_presence)

    response = client.post(
        "/api/webhooks/gowa",
        json={
            "event": "message",
            "payload": {
                "from": "2349025283155@s.whatsapp.net",
                "body": "check this payment document",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_credits"
    assert sent_typing == ["2349025283155@s.whatsapp.net"]
    assert sent_messages == [
        (
            "2349025283155@s.whatsapp.net",
            "Your Sentra verification credits are exhausted. Recharge your credits before submitting another payment document.",
        )
    ]


def test_gowa_webhook_starts_verification_with_typing_and_ack(monkeypatch):
    client = TestClient(app)
    sent_messages: list[tuple[str, str]] = []
    sent_typing: list[str] = []
    enqueued: list[int] = []

    class Decision:
        action = "start_verification"
        reply_text = "We are checking your payment document now."
        start_verification = True

    async def fake_decide_inbound_action(db, payload):
        return Decision()

    async def fake_create_request_from_gowa_event(db, payload):
        return 91

    async def fake_send_text(self, to: str, text: str) -> None:
        sent_messages.append((to, text))

    async def fake_send_chat_presence(self, to: str, presence: str = "composing", media_type: str = "text") -> None:
        sent_typing.append(to)

    monkeypatch.setattr("app.api.routes.webhooks.decide_inbound_action", fake_decide_inbound_action)
    monkeypatch.setattr("app.api.routes.webhooks.create_request_from_gowa_event", fake_create_request_from_gowa_event)
    monkeypatch.setattr("app.api.routes.webhooks.GowaClient.send_text", fake_send_text)
    monkeypatch.setattr("app.api.routes.webhooks.GowaClient.send_chat_presence", fake_send_chat_presence)
    monkeypatch.setattr("app.api.routes.webhooks.worker_queue.enqueue", lambda request_id: enqueued.append(request_id))

    response = client.post(
        "/api/webhooks/gowa",
        json={
            "event": "message",
            "payload": {
                "from": "2349025283155@s.whatsapp.net",
                "image": {
                    "url": "/media/proof.png",
                    "filename": "proof.png",
                },
                "body": "check this",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["request_id"] == 91
    assert sent_typing == ["2349025283155@s.whatsapp.net"]
    assert sent_messages == [("2349025283155@s.whatsapp.net", "We are checking your payment document now.")]
    assert enqueued == [91]
