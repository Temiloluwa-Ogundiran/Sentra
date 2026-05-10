from pathlib import Path
from shutil import copyfile

from PIL import Image, ImageDraw

from app.core.config import settings


def annotate_artifact(source_path: Path, artifact_type: str, reasons: list[str], request_id: int) -> Path:
    target = settings.storage_root / "annotated" / f"{request_id}_{source_path.stem}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    if source_path.suffix.lower() == ".pdf":
        # placeholder until PDF rendering pipeline is implemented fully
        target.write_text("PDF annotation preview placeholder", encoding="utf-8")
        return target

    with Image.open(source_path) as image:
        draw = ImageDraw.Draw(image)
        width, height = image.size
        draw.rectangle([(width * 0.55, height * 0.2), (width * 0.92, height * 0.35)], outline="red", width=4)
        draw.text((10, 10), artifact_type, fill="red")
        image.save(target)
    return target
