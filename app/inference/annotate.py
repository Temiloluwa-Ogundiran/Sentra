from pathlib import Path

import fitz
from PIL import Image, ImageDraw

from app.core.config import settings
from app.inference.quality import find_visible_edit_regions


def annotate_artifact(source_path: Path, artifact_type: str, reasons: list[str], request_id: int) -> Path:
    target = settings.storage_root / "annotated" / f"{request_id}_{source_path.stem}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    if source_path.suffix.lower() == ".pdf":
        document = fitz.open(source_path)
        page = document.load_page(0)
        pixmap = page.get_pixmap()
        image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
        draw = ImageDraw.Draw(image)
        draw.text((10, 10), artifact_type, fill="red")
        if reasons:
            draw.text((10, 35), reasons[0][:120], fill="red")
        image.save(target)
        document.close()
        return target

    with Image.open(source_path) as image:
        draw = ImageDraw.Draw(image)
        regions = find_visible_edit_regions(source_path)
        for min_x, min_y, max_x, max_y in regions:
            draw.rectangle([(min_x, min_y), (max_x, max_y)], outline="red", width=4)
        draw.text((10, 10), artifact_type, fill="red")
        image.save(target)
    return target
