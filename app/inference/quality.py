from pathlib import Path

import fitz
import numpy as np
from PIL import Image


def assess_quality(file_path: Path) -> list[str]:
    flags: list[str] = []
    try:
        if file_path.suffix.lower() == ".pdf":
            document = fitz.open(file_path)
            try:
                page = document.load_page(0)
                width, height = page.rect.width, page.rect.height
            finally:
                document.close()
        else:
            with Image.open(file_path) as image:
                width, height = image.size
                rgb = np.array(image.convert("RGB"))
                red_mask = (rgb[:, :, 0] > 180) & (rgb[:, :, 1] < 110) & (rgb[:, :, 2] < 110)
                if red_mask.mean() > 0.01:
                    flags.append("edited_overlay_signal")
        if width < 400 or height < 400:
            flags.append("low_resolution")
    except Exception:
        flags.append("unreadable_artifact")
    return flags
