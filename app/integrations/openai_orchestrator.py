import json
from dataclasses import dataclass

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class ModelOrchestratorResponse:
    action: str
    reply_text: str | None = None


async def choose_orchestrator_action(context: dict, allowed_actions: list[str]) -> ModelOrchestratorResponse | None:
    if not settings.openai_api_key:
        return None

    try:
        from openai import AsyncOpenAI
    except ImportError:
        logger.warning(
            "openai package unavailable for orchestrator",
            extra={"extra_payload": {"allowed_actions": allowed_actions}},
        )
        return None

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": allowed_actions},
            "reply_text": {"type": ["string", "null"]},
        },
        "required": ["action", "reply_text"],
        "additionalProperties": False,
    }

    try:
        response = await client.responses.create(
            model=settings.openai_orchestrator_model,
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You route WhatsApp verification assistant messages. "
                                "Choose exactly one action from the allowed list and provide a short, warm, plain-English reply. "
                                "Always talk about credits, never dollars or wallet currency. "
                                "Refer to uploads as payment documents, not proofs. "
                                "Never claim payment settlement was verified."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": json.dumps({"allowed_actions": allowed_actions, "context": context}),
                        }
                    ],
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "sentra_orchestrator_action",
                    "schema": schema,
                    "strict": True,
                }
            },
        )
        output_text = getattr(response, "output_text", "").strip()
        if not output_text:
            return None
        payload = json.loads(output_text)
    except Exception:
        logger.exception(
            "openai orchestrator failed",
            extra={"extra_payload": {"allowed_actions": allowed_actions, "context": context}},
        )
        return None
    finally:
        try:
            await client.close()
        except Exception:
            logger.debug("openai client close failed")

    action = payload.get("action")
    if action not in allowed_actions:
        return None
    return ModelOrchestratorResponse(action=action, reply_text=payload.get("reply_text"))
