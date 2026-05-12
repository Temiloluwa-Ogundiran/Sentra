from functools import lru_cache
from pathlib import Path
import re

import fitz
from PIL import Image, ImageOps

from app.schemas.common import ExtractedFields


@lru_cache(maxsize=1)
def get_reader():
    import easyocr

    return easyocr.Reader(["en"], gpu=False)


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _extract_with_patterns(raw_text: str) -> ExtractedFields:
    upper_text = raw_text.upper()
    amount_match = re.search(
        r"(?:AMOUNT\s*/\s*SURCHARGE|AMOUNT|TOTAL)[^\d₦N]*[₦N]?\s*([\d,]+(?:\.\d{2})?)",
        raw_text,
        re.IGNORECASE,
    )
    date_match = re.search(r"(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", raw_text)
    time_match = re.search(r"\b(\d{1,2}:\d{2}\s?(?:AM|PM)?)\b", raw_text, re.IGNORECASE)
    payment_reference_match = re.search(
        r"(?:PAYMENT REFERENCE)[:\s]*([A-Z0-9|/_-]{6,})",
        raw_text,
        re.IGNORECASE,
    )
    request_reference_match = re.search(
        r"(?:REQUEST REFERENCE|REFERENCE|REF)[:\s]*([A-Z0-9|/_-]{6,})",
        raw_text,
        re.IGNORECASE,
    )
    provider_match = re.search(r"(?:BANK|PROVIDER|NETWORK)[:\s]*([^\n]+)", raw_text, re.IGNORECASE)
    recipient_match = re.search(
        r"(?:CUSTOMER NAME|RECIPIENT|BENEFICIARY|ACCOUNT NAME|NAME)[:\s]*([^\n]+)",
        raw_text,
        re.IGNORECASE,
    )

    reference_match = payment_reference_match or request_reference_match

    return ExtractedFields(
        amount=amount_match.group(1).replace(",", "") if amount_match else "Not detected",
        currency="NGN" if ("₦" in raw_text or "NGN" in upper_text or amount_match is not None) else "Not detected",
        date=date_match.group(1) if date_match else "Not detected",
        time=time_match.group(1).upper() if time_match else "Not detected",
        reference=_normalize_whitespace(reference_match.group(1)) if reference_match else "Not detected",
        provider=_normalize_whitespace(provider_match.group(1)) if provider_match else "Not detected",
        recipient_label=_normalize_whitespace(recipient_match.group(1)) if recipient_match else "Not detected",
    )


def _extract_pdf_text(file_path: Path) -> str:
    document = fitz.open(file_path)
    try:
        pages = [page.get_text() for page in document]
        return "\n".join(chunk for chunk in pages if chunk.strip())
    finally:
        document.close()


def _extract_tesseract_text(file_path: Path) -> str:
    try:
        import pytesseract
    except Exception:
        return ""

    with Image.open(file_path) as image:
        prepared = ImageOps.autocontrast(image.convert("L"))
        if min(prepared.size) < 1200:
            scale = max(1, int(1200 / max(1, min(prepared.size))))
            prepared = prepared.resize((prepared.width * scale, prepared.height * scale))
        return pytesseract.image_to_string(prepared, config="--psm 6").strip()


def _looks_informative(text: str) -> bool:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) >= 40:
        return True
    keywords = ("amount", "reference", "transaction", "bank", "beneficiary", "successful", "date")
    upper = cleaned.lower()
    return sum(1 for keyword in keywords if keyword in upper) >= 2


def run_ocr(file_path: Path) -> tuple[str, ExtractedFields]:
    try:
        if file_path.suffix.lower() == ".pdf":
            raw_text = _extract_pdf_text(file_path)
        else:
            raw_text = _extract_tesseract_text(file_path)
            if not _looks_informative(raw_text):
                result = get_reader().readtext(str(file_path), detail=0, paragraph=True)
                raw_text = "\n".join(result)
    except Exception:
        raw_text = ""

    return raw_text, _extract_with_patterns(raw_text)
