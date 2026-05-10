from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dev import DevUploadResponse
from app.services.requests import create_request_from_upload
from app.workers.queue import worker_queue

router = APIRouter()


@router.post("/upload", response_model=DevUploadResponse)
async def upload_for_analysis(
    file: UploadFile = File(...),
    expected_amount: str | None = Form(default=None),
    caption: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> DevUploadResponse:
    request_id = await create_request_from_upload(
        db=db,
        whatsapp_id="dev-user",
        upload_file=file,
        expected_amount=expected_amount,
        caption=caption,
    )
    worker_queue.enqueue(request_id)
    return DevUploadResponse(request_id=request_id)


@router.get("/requests/{request_id}")
def get_result(request_id: int, db: Session = Depends(get_db)) -> dict:
    from app.services.requests import fetch_result_payload

    return fetch_result_payload(db, request_id)
