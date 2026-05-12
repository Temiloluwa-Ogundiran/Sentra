from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dev import DevRechargeResponse, DevUploadResponse, DevWalletResponse
from app.services.payments import initiate_recharge_checkout
from app.services.requests import create_request_from_upload, get_or_create_user
from app.services.wallets import InsufficientCreditsError, get_or_create_wallet
from app.workers.queue import worker_queue

router = APIRouter()


@router.post("/upload", response_model=DevUploadResponse)
async def upload_for_analysis(
    file: UploadFile = File(...),
    expected_amount: str | None = Form(default=None),
    caption: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> DevUploadResponse:
    try:
        request_id = await create_request_from_upload(
            db=db,
            whatsapp_id="dev-user",
            upload_file=file,
            expected_amount=expected_amount,
            caption=caption,
        )
    except InsufficientCreditsError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    worker_queue.enqueue(request_id)
    return DevUploadResponse(request_id=request_id)


@router.get("/requests/{request_id}")
def get_result(request_id: int, db: Session = Depends(get_db)) -> dict:
    from app.services.requests import fetch_result_payload

    return fetch_result_payload(db, request_id)


@router.get("/wallet/{whatsapp_id}", response_model=DevWalletResponse)
def get_wallet(whatsapp_id: str, db: Session = Depends(get_db)) -> DevWalletResponse:
    user = get_or_create_user(db, whatsapp_id)
    wallet = get_or_create_wallet(db, user.id)
    return DevWalletResponse(
        whatsapp_id=whatsapp_id,
        balance=wallet.balance,
        status=wallet.status,
        last_payment_reference=wallet.last_payment_reference,
    )


@router.post("/wallet/recharge", response_model=DevRechargeResponse)
async def recharge_wallet(
    whatsapp_id: str = Form(...),
    customer_email: str = Form(...),
    amount_kobo: int = Form(...),
    credits_to_add: int = Form(...),
    db: Session = Depends(get_db),
) -> DevRechargeResponse:
    user = get_or_create_user(db, whatsapp_id)
    wallet = get_or_create_wallet(db, user.id)
    transaction, checkout = await initiate_recharge_checkout(
        db,
        user=user,
        customer_email=customer_email,
        amount_kobo=amount_kobo,
        credits_to_add=credits_to_add,
    )
    return DevRechargeResponse(
        whatsapp_id=whatsapp_id,
        balance=wallet.balance,
        transaction_ref=transaction.transaction_ref,
        status=transaction.status,
        checkout=checkout,
    )
