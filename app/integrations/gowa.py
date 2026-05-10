from pathlib import Path

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
            await client.post(
                f"{self.base_url}/api/send/text",
                json={"phone": to, "message": text},
                headers=self.headers,
                auth=self.auth,
            )

    async def send_file(self, to: str, file_path: Path, caption: str | None = None) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(
                f"{self.base_url}/api/send/file",
                json={"phone": to, "filePath": str(file_path), "caption": caption or ""},
                headers=self.headers,
                auth=self.auth,
            )

    async def fetch_media_bytes(self, media_url: str) -> bytes:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(media_url, headers=self.headers, auth=self.auth)
            response.raise_for_status()
            return response.content
