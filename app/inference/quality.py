from pathlib import Path

import fitz
import numpy as np
from PIL import Image


def _has_marker_overlay(rgb: np.ndarray) -> bool:
    height, width = rgb.shape[:2]
    top = int(height * 0.14)
    bottom = int(height * 0.25)
    left = int(width * 0.18)
    right = int(width * 0.62)
    if bottom <= top or right <= left:
        return False

    region = rgb[top:bottom, left:right]
    marker_mask = (
        (region[:, :, 1] > 180)
        & (region[:, :, 0] < 180)
        & (region[:, :, 2] < 180)
    )
    if not marker_mask.any():
        return False

    visited = np.zeros(marker_mask.shape, dtype=bool)
    best_area = 0
    best_fill = 0.0

    for start_y, start_x in np.argwhere(marker_mask):
        if visited[start_y, start_x]:
            continue
        stack = [(int(start_y), int(start_x))]
        visited[start_y, start_x] = True
        area = 0
        min_x = max_x = int(start_x)
        min_y = max_y = int(start_y)

        while stack:
            y, x = stack.pop()
            area += 1
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)

            for next_y, next_x in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if (
                    0 <= next_y < marker_mask.shape[0]
                    and 0 <= next_x < marker_mask.shape[1]
                    and marker_mask[next_y, next_x]
                    and not visited[next_y, next_x]
                ):
                    visited[next_y, next_x] = True
                    stack.append((next_y, next_x))

        bbox_area = (max_x - min_x + 1) * (max_y - min_y + 1)
        fill_ratio = area / max(bbox_area, 1)
        if area > best_area:
            best_area = area
            best_fill = fill_ratio

    return best_area >= 700 and best_fill >= 0.45


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
                elif _has_marker_overlay(rgb):
                    flags.append("edited_overlay_signal")
        if width < 400 or height < 400:
            flags.append("low_resolution")
    except Exception:
        flags.append("unreadable_artifact")
    return flags
