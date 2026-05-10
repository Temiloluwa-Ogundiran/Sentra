import json
from pathlib import Path

import boto3

from app.core.config import settings


class BedrockClient:
    def __init__(self) -> None:
        self.runtime = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
            aws_session_token=settings.aws_session_token or None,
        )

    def analyze_artifact(self, model_id: str, image_bytes: bytes, image_format: str, prompt: str) -> dict:
        response = self.runtime.converse(
            modelId=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"text": prompt},
                        {
                            "image": {
                                "format": image_format,
                                "source": {"bytes": image_bytes},
                            }
                        },
                    ],
                }
            ],
        )
        content = response.get("output", {}).get("message", {}).get("content", [])
        text_parts = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("text")]
        raw_text = "\n".join(part for part in text_parts if part).strip()
        try:
            parsed = json.loads(raw_text) if raw_text else {}
        except json.JSONDecodeError:
            parsed = {"raw_text": raw_text}
        if raw_text and "raw_text" not in parsed:
            parsed["raw_text"] = raw_text
        return parsed
