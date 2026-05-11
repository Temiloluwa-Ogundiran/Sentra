import json

import httpx

from app.core.config import settings


class ModalClient:
    def __init__(self) -> None:
        self.timeout = httpx.Timeout(60.0, connect=10.0)
        self.headers = {"Content-Type": "application/json"}

    def invoke_json(self, endpoint_url: str, payload: dict) -> dict:
        response = httpx.post(
            endpoint_url,
            headers=self.headers,
            content=json.dumps(payload).encode("utf-8"),
            timeout=self.timeout,
        )
        response.raise_for_status()
        try:
            return response.json()
        except json.JSONDecodeError:
            return {"raw": response.text}
