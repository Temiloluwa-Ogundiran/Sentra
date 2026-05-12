from pathlib import Path
from urllib.parse import urljoin

import httpx

from app.core.config import settings


class GowaClient:
    def __init__(self) -> None:
        self.base_url = settings.gowa_base_url.rstrip("/")
        self.auth = (
            (settings.gowa_basic_auth_user, settings.gowa_basic_auth_password)
            if settings.gowa_basic_auth_user and settings.gowa_basic_auth_password
            else None
        )
        self.device_id = settings.gowa_device_id
        self.headers = {"X-Device-ID": self.device_id} if self.device_id else {}

    async def send_text(self, to: str, text: str) -> None:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.base_url}/send/message",
                json={"phone": to, "message": text},
                headers=self.headers,
                auth=self.auth,
            )
            response.raise_for_status()

    async def send_file(self, to: str, file_path: Path, caption: str | None = None) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            with file_path.open("rb") as file_handle:
                response = await client.post(
                    f"{self.base_url}/send/file",
                    data={
                        "phone": to,
                        "caption": caption or "",
                        "is_forwarded": "false",
                    },
                    files={"file": (file_path.name, file_handle, "application/octet-stream")},
                    headers=self.headers,
                    auth=self.auth,
                )
            response.raise_for_status()

    async def send_chat_presence(self, to: str, presence: str = "composing", media_type: str = "text") -> None:
        action = "stop" if presence in {"paused", "stop"} else "start"
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.base_url}/send/chat-presence",
                json={"phone": to, "action": action},
                headers=self.headers,
                auth=self.auth,
            )
            response.raise_for_status()

    async def fetch_media_bytes(self, media_url: str) -> bytes:
        resolved_url = media_url if media_url.startswith(("http://", "https://")) else urljoin(
            f"{self.base_url}/", media_url.lstrip("/")
        )
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(resolved_url, headers=self.headers, auth=self.auth)
            response.raise_for_status()
            return response.content
