from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services.readiness import get_readiness_status

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
def ready() -> tuple[dict, int] | dict:
    status = get_readiness_status()
    if status["status"] == "ready":
        return status
    return JSONResponse(content=status, status_code=503)
