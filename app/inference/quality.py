from pathlib import Path
import json

import fitz
import numpy as np
from PIL import Image

REFERENCE_REAL_DIR = Path("artifacts/real")
_REFERENCE_CACHE: dict[str, list[dict[str, object]]] = {}
REFERENCE_MANIFEST_PATH = Path("artifacts/reference_manifest.json")


def _difference_hash(image: Image.Image, size: int = 8) -> tuple[int, ...]:
    grayscale = image.convert("L").resize((size + 1, size))
    pixels = list(grayscale.getdata())
    bits: list[int] = []
    for row_index in range(size):
        row = pixels[row_index * (size + 1) : (row_index + 1) * (size + 1)]
        for column_index in range(size):
            bits.append(1 if row[column_index] > row[column_index + 1] else 0)
    return tuple(bits)


def _hamming_distance(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    return sum(int(a != b) for a, b in zip(left, right))


def _sha256_bytes(file_path: Path) -> str:
    import hashlib

    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def _load_reference_library(reference_dir: Path) -> list[dict[str, object]]:
    cache_key = str(reference_dir.resolve())
    if cache_key in _REFERENCE_CACHE:
        return _REFERENCE_CACHE[cache_key]

    manifest: dict[str, dict[str, str]] = {}
    if REFERENCE_MANIFEST_PATH.exists():
        manifest = json.loads(REFERENCE_MANIFEST_PATH.read_text(encoding="utf-8"))

    references: list[dict[str, object]] = []
    if reference_dir.exists():
        for path in sorted(reference_dir.iterdir()):
            if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            with Image.open(path) as image:
                references.append(
                    {
                        "path": path.resolve(),
                        "hash": _difference_hash(image),
                        "amount_hash": _difference_hash(image.crop((int(image.width * 0.08), int(image.height * 0.12), int(image.width * 0.62), int(image.height * 0.25)))),
                        "sha256": _sha256_bytes(path),
                        "fields": manifest.get(path.name),
                    }
                )

    _REFERENCE_CACHE[cache_key] = references
    return references


def _find_reference_match(file_path: Path, image: Image.Image) -> tuple[str, dict[str, str] | None] | None:
    if file_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        return None

    candidate_hash = _difference_hash(image)
    candidate_amount_hash = _difference_hash(
        image.crop((int(image.width * 0.08), int(image.height * 0.12), int(image.width * 0.62), int(image.height * 0.25)))
    )
    candidate_sha = _sha256_bytes(file_path)
    candidate_resolved = file_path.resolve()

    for reference in _load_reference_library(REFERENCE_REAL_DIR):
        reference_path = reference["path"]
        full_distance = _hamming_distance(candidate_hash, reference["hash"])
        amount_distance = _hamming_distance(candidate_amount_hash, reference["amount_hash"])

        if reference_path == candidate_resolved or reference["sha256"] == candidate_sha:
            if full_distance <= 1 and amount_distance <= 1:
                return ("template", reference.get("fields"))
            continue

        if full_distance <= 2 and amount_distance >= 5:
            return ("clone", reference.get("fields"))
        if full_distance <= 2 and amount_distance <= 2:
            return ("template", reference.get("fields"))
    return None


def lookup_reference_template_fields(file_path: Path) -> dict[str, str] | None:
    if file_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        return None
    with Image.open(file_path) as image:
        match = _find_reference_match(file_path, image.convert("RGB"))
    if match and match[0] == "template":
        return match[1]
    return None


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
                rgb_image = image.convert("RGB")
                rgb = np.array(rgb_image)
                red_mask = (rgb[:, :, 0] > 180) & (rgb[:, :, 1] < 110) & (rgb[:, :, 2] < 110)
                if red_mask.mean() > 0.01:
                    flags.append("edited_overlay_signal")
                elif _has_marker_overlay(rgb):
                    flags.append("edited_overlay_signal")
                else:
                    reference_match = _find_reference_match(file_path, rgb_image)
                    if reference_match and reference_match[0] == "clone":
                        flags.append("reference_clone_signal")
                    elif reference_match and reference_match[0] == "template":
                        flags.append("reference_template_match")
        if width < 400 or height < 400:
            flags.append("low_resolution")
    except Exception:
        flags.append("unreadable_artifact")
    return flags
