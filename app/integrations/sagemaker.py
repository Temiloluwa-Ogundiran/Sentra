import json

import boto3

from app.core.config import settings


class SageMakerClient:
    def __init__(self) -> None:
        self.runtime = boto3.client(
            "sagemaker-runtime",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
            aws_session_token=settings.aws_session_token or None,
        )

    def invoke_json(self, endpoint_name: str, payload: dict) -> dict:
        response = self.runtime.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType="application/json",
            Body=json.dumps(payload).encode("utf-8"),
        )
        body = response["Body"].read().decode("utf-8")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"raw": body}
