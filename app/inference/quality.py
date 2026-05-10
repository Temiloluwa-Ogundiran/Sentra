from pathlib import Path

from PIL import Image


def assess_quality(file_path: Path) -> list[str]:
    flags: list[str] = []
    try:
        with Image.open(file_path) as image:
            width, height = image.size
            if width < 400 or height < 400:
                flags.append("low_resolution")
    except Exception:
        flags.append("unreadable_artifact")
    return flags
