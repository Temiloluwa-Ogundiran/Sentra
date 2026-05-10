from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings


async def persist_upload(upload_file: UploadFile, prefix: str = "") -> tuple[Path, int]:
    suffix = Path(upload_file.filename or "artifact.bin").suffix
    target = settings.storage_root / "uploads" / f"{prefix}{uuid4().hex}{suffix}"
    target.parent.mkdir(parents=True, exist_ok=True)
    content = await upload_file.read()
    target.write_bytes(content)
    return target, len(content)


def persist_bytes(content: bytes, filename: str) -> tuple[Path, int]:
    target = settings.storage_root / "uploads" / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return target, len(content)
