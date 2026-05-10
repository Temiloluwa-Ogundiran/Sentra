from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.requests import create_request_from_gowa_event
from app.workers.queue import worker_queue

router = APIRouter()


@router.post("/gowa")
async def gowa_webhook(
    payload: dict,
    db: Session = Depends(get_db),
) -> dict:
    request_id = await create_request_from_gowa_event(db=db, payload=payload)
    if request_id is not None:
        worker_queue.enqueue(request_id)
    return {"status": "accepted", "request_id": request_id}
