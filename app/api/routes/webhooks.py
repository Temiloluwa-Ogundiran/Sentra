from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.integrations.gowa import GowaClient
from app.services.orchestrator import decide_inbound_action
from app.services.payments import process_squad_webhook
from app.services.requests import create_request_from_gowa_event
from app.services.wallets import InsufficientCreditsError
from app.workers.queue import worker_queue

router = APIRouter()
logger = get_logger(__name__)


@router.post("/gowa")
async def gowa_webhook(
    payload: dict,
    db: Session = Depends(get_db),
) -> dict:
    event_name = payload.get("event")
    message_payload = payload.get("payload", {})
    sender = message_payload.get("from")
    logger.info(
        "received gowa webhook",
        extra={
            "extra_payload": {
                "event": event_name,
                "sender": sender,
                "has_body": bool(message_payload.get("body")),
                "has_image": bool(message_payload.get("image")),
                "has_document": bool(message_payload.get("document")),
            }
        },
    )
    decision = await decide_inbound_action(db, payload)
    logger.info(
        "resolved inbound action",
        extra={"extra_payload": {"event": event_name, "sender": sender, "action": decision.action}},
    )
    if decision.action == "ignore":
        return {"status": "ignored", "request_id": None}

    request_id = None
    try:
        if decision.start_verification:
            if sender:
                await GowaClient().send_chat_presence(sender)
            request_id = await create_request_from_gowa_event(db=db, payload=payload)
            if sender and decision.reply_text:
                await GowaClient().send_text(sender, decision.reply_text)
            worker_queue.enqueue(request_id)
        elif sender and decision.reply_text:
            await GowaClient().send_chat_presence(sender)
            await GowaClient().send_text(sender, decision.reply_text)
    except InsufficientCreditsError:
        if sender and decision.reply_text:
            await GowaClient().send_chat_presence(sender)
            await GowaClient().send_text(sender, decision.reply_text)
        return {"status": "insufficient_credits", "request_id": None}
    return {"status": "accepted", "request_id": request_id}


@router.post("/squad")
async def squad_webhook(request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()
    payload = await request.json()
    status_code, response_payload = await process_squad_webhook(
        db,
        raw_body=raw_body,
        payload=payload,
        header_signature=request.headers.get("x-squad-encrypted-body"),
        secret_key=settings.squad_secret_key,
    )
    return JSONResponse(content=response_payload, status_code=status_code)
