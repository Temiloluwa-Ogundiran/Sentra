from pydantic import BaseModel, Field


class DevUploadResponse(BaseModel):
    request_id: int
    status: str = Field(default="accepted")


class DevWalletResponse(BaseModel):
    whatsapp_id: str
    balance: int
    status: str
    last_payment_reference: str | None = None


class DevRechargeResponse(BaseModel):
    whatsapp_id: str
    balance: int
    transaction_ref: str
    status: str
    checkout: dict
