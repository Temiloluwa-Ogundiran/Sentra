from pathlib import Path

from sqlalchemy import text

from app.core.config import settings
from app.db.base import SessionLocal

def get_readiness_status() -> dict:
    checks = {}
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error:{exc}"

    try:
        import easyocr  # noqa: F401

        checks["ocr"] = "ok"
    except Exception as exc:
        checks["ocr"] = f"error:{exc}"

    try:
        root = Path(settings.storage_root)
        root.mkdir(parents=True, exist_ok=True)
        checks["storage"] = "ok" if root.exists() and root.is_dir() else "error:missing"
    except Exception as exc:
        checks["storage"] = f"error:{exc}"

    if settings.readiness_require_hosted:
        checks["hosted_inference"] = (
            "ok"
            if (
                settings.hosted_artifact_reasoner_url
                and settings.hosted_tamper_detector_url
                and settings.hosted_synthetic_artifact_detector_url
            )
            else "error:missing_endpoint_configuration"
        )

    status = "ready" if all(str(value) == "ok" for value in checks.values()) else "not_ready"
    return {"status": status, "checks": checks}
