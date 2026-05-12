from pathlib import Path

import pytest

from app.integrations.gowa import GowaClient


@pytest.mark.asyncio
async def test_send_file_uses_multipart_upload(monkeypatch, tmp_path):
    artifact = tmp_path / "annotated.png"
    artifact.write_bytes(b"fake-image-bytes")
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

    async def fake_post(self, url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        file_tuple = kwargs["files"]["file"]
        captured["filename"] = file_tuple[0]
        captured["body"] = file_tuple[1].read()
        return FakeResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

    client = GowaClient()
    await client.send_file("2348012345678", artifact, caption="Sentra analysis preview")

    assert captured["url"].endswith("/send/file")
    assert captured["kwargs"]["data"]["phone"] == "2348012345678"
    assert captured["kwargs"]["data"]["caption"] == "Sentra analysis preview"
    assert captured["kwargs"]["data"]["is_forwarded"] == "false"
    assert captured["filename"] == "annotated.png"
    assert captured["body"] == b"fake-image-bytes"


@pytest.mark.asyncio
async def test_send_image_uses_image_endpoint(monkeypatch, tmp_path):
    artifact = tmp_path / "annotated.png"
    artifact.write_bytes(b"fake-image-bytes")
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

    async def fake_post(self, url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        file_tuple = kwargs["files"]["image"]
        captured["filename"] = file_tuple[0]
        captured["body"] = file_tuple[1].read()
        captured["mime"] = file_tuple[2]
        return FakeResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

    client = GowaClient()
    await client.send_image("2348012345678", artifact, caption="Sentra analysis preview")

    assert captured["url"].endswith("/send/image")
    assert captured["kwargs"]["data"]["phone"] == "2348012345678"
    assert captured["kwargs"]["data"]["caption"] == "Sentra analysis preview"
    assert captured["filename"] == "annotated.png"
    assert captured["mime"] == "image/png"
    assert captured["body"] == b"fake-image-bytes"
