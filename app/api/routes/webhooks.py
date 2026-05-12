from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.services.payments import process_squad_webhook
from app.services.requests import create_request_from_gowa_event
from app.services.wallets import InsufficientCreditsError
from app.workers.queue import worker_queue

router = APIRouter()


@router.post("/gowa")
async def gowa_webhook(
    payload: dict,
    db: Session = Depends(get_db),
) -> dict:
    try:
        request_id = await create_request_from_gowa_event(db=db, payload=payload)
    except InsufficientCreditsError:
        return {"status": "insufficient_credits", "request_id": None}
    if request_id is not None:
        worker_queue.enqueue(request_id)
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
