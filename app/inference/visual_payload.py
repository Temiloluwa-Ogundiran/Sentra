import base64
import io
from pathlib import Path

import fitz
from PIL import Image


def prepare_visual_payload(file_path: Path) -> tuple[str, bytes, str]:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        document = fitz.open(file_path)
        page = document.load_page(0)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        png_bytes = pixmap.tobytes("png")
        document.close()
        return base64.b64encode(png_bytes).decode("utf-8"), png_bytes, "png"

    with Image.open(file_path) as image:
        converted = image.convert("RGB")
        buffer = io.BytesIO()
        image_format = "png" if suffix == ".png" else "jpeg"
        converted.save(buffer, format=image_format.upper())
        image_bytes = buffer.getvalue()
        return base64.b64encode(image_bytes).decode("utf-8"), image_bytes, image_format
