from functools import lru_cache
from pathlib import Path

from app.schemas.common import ExtractedFields


@lru_cache(maxsize=1)
def get_reader():
    import easyocr

    return easyocr.Reader(["en"], gpu=False)


def run_ocr(file_path: Path) -> tuple[str, ExtractedFields]:
    try:
        result = get_reader().readtext(str(file_path), detail=0, paragraph=True)
        raw_text = "\n".join(result)
    except Exception:
        raw_text = ""

    normalized = ExtractedFields(
        amount="Not detected",
        currency="NGN" if "₦" in raw_text or "NGN" in raw_text.upper() else "Not detected",
        date="Not detected",
        time="Not detected",
        reference="Not detected",
        provider="Not detected",
        recipient_label="Not detected",
    )
    return raw_text, normalized
