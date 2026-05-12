from pathlib import Path

from app.db.base import Base
from app.models.artifact import Artifact
from app.models.user import User
from app.models.verification_request import VerificationRequest
from app.services.requests import create_request_from_gowa_event
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


async def test_webhook_ignores_unsupported_event(monkeypatch, tmp_path):
    session_local = _make_session()
    monkeypatch.setattr("app.services.storage.settings.storage_root", tmp_path)

    payload = {
        "event": "message.ack",
        "device_id": "2348012345678@s.whatsapp.net",
        "payload": {"id": "abc123"},
    }

    with session_local() as db:
        request_id = await create_request_from_gowa_event(db, payload)
        count = db.query(VerificationRequest).count()

    assert request_id is None
    assert count == 0


async def test_webhook_creates_request_for_supported_image(monkeypatch, tmp_path):
    session_local = _make_session()
    monkeypatch.setattr("app.services.storage.settings.storage_root", tmp_path)
    monkeypatch.setattr("app.services.requests.consume_verification_credit", lambda db, wallet, cost=1: wallet)

    async def fake_fetch_media_bytes(self, media_url: str) -> bytes:
        assert media_url == "https://example.com/proof.png"
        return b"image-bytes"

    monkeypatch.setattr("app.services.requests.GowaClient.fetch_media_bytes", fake_fetch_media_bytes)

    event = {
        "event": "message",
        "device_id": "2348012345678@s.whatsapp.net",
        "payload": {
            "id": "msg1",
            "chat_id": "2348099999999@s.whatsapp.net",
            "from": "2348099999999@s.whatsapp.net",
            "from_name": "Demo User",
            "timestamp": "2026-05-12T10:30:00Z",
            "body": "please verify",
            "image": {"url": "https://example.com/proof.png", "caption": "please verify"},
        },
    }

    with session_local() as db:
        request_id = await create_request_from_gowa_event(db, event)
        request = db.get(VerificationRequest, request_id)
        artifact = db.query(Artifact).filter(Artifact.request_id == request_id).one()
        user = db.query(User).filter(User.id == request.user_id).one()

    assert request is not None
    assert request.status == "received"
    assert request.caption == "please verify"
    assert user.whatsapp_id == "2348099999999@s.whatsapp.net"
    assert artifact.mime_type == "image/png"
    assert Path(artifact.source_path).exists()


async def test_webhook_uses_first_supported_media(monkeypatch, tmp_path):
    session_local = _make_session()
    monkeypatch.setattr("app.services.storage.settings.storage_root", tmp_path)
    monkeypatch.setattr("app.services.requests.consume_verification_credit", lambda db, wallet, cost=1: wallet)

    called_urls: list[str] = []

    async def fake_fetch_media_bytes(self, media_url: str) -> bytes:
        called_urls.append(media_url)
        return b"media-bytes"

    monkeypatch.setattr("app.services.requests.GowaClient.fetch_media_bytes", fake_fetch_media_bytes)

    event = {
        "event": "message",
        "device_id": "2348012345678@s.whatsapp.net",
        "payload": {
            "id": "msg2",
            "chat_id": "2348099999999@s.whatsapp.net",
            "from": "2348099999999@s.whatsapp.net",
            "timestamp": "2026-05-12T10:30:00Z",
            "body": "check both",
            "image": {"url": "https://example.com/proof.png", "caption": "check both"},
            "document": {"url": "https://example.com/proof.pdf", "filename": "proof.pdf"},
        },
    }

    with session_local() as db:
        request_id = await create_request_from_gowa_event(db, event)
        artifact = db.query(Artifact).filter(Artifact.request_id == request_id).one()

    assert called_urls == ["https://example.com/proof.png"]
    assert artifact.original_filename == "proof.png"
