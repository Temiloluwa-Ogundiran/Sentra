from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


REAL_DIR = Path("artifacts/real")
FAKE_DIR = Path("artifacts/fake")


def _load_font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size=size)
    except Exception:
        return ImageFont.load_default()


def _draw_fake_amount(image: Image.Image) -> Image.Image:
    edited = image.copy().convert("RGB")
    draw = ImageDraw.Draw(edited)
    width, height = edited.size
    box = (int(width * 0.05), int(height * 0.12), int(width * 0.72), int(height * 0.23))
    draw.rounded_rectangle(box, radius=12, fill="white")
    draw.text((box[0] + 14, box[1] + 6), "DEBIT", fill="#3b82f6", font=_load_font(18))
    draw.text((box[0] + 12, box[1] + 34), "₦94,000.00", fill="black", font=_load_font(34))
    return edited


def _draw_fake_reference(image: Image.Image) -> Image.Image:
    edited = image.copy().convert("RGB")
    draw = ImageDraw.Draw(edited)
    width, height = edited.size
    box = (int(width * 0.08), int(height * 0.78), int(width * 0.92), int(height * 0.89))
    draw.rectangle(box, fill="white")
    draw.text((box[0] + 10, box[1] + 8), "Transaction Reference", fill="gray", font=_load_font(18))
    draw.text((box[0] + 10, box[1] + 38), "TRF|EDITED|999999999999999999999", fill="black", font=_load_font(20))
    return edited


def _apply_obvious_tamper(image: Image.Image) -> Image.Image:
    edited = _draw_fake_amount(image)
    edited = _draw_fake_reference(edited)
    overlay = Image.new("RGBA", edited.size, (255, 255, 255, 0))
    width, height = edited.size
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle(
        (int(width * 0.55), int(height * 0.12), int(width * 0.93), int(height * 0.22)),
        outline=(255, 0, 0, 220),
        width=4,
    )
    banner = (int(width * 0.52), int(height * 0.03), int(width * 0.94), int(height * 0.09))
    overlay_draw.rounded_rectangle(banner, radius=10, fill=(220, 38, 38, 235))
    overlay_draw.text((banner[0] + 12, banner[1] + 8), "EDITED", fill=(255, 255, 255, 255), font=_load_font(24))
    center_banner = Image.new("RGBA", edited.size, (255, 255, 255, 0))
    center_draw = ImageDraw.Draw(center_banner)
    center_draw.text(
        (int(width * 0.18), int(height * 0.46)),
        "ALTERED PROOF",
        fill=(200, 0, 0, 180),
        font=_load_font(42),
    )
    center_banner = center_banner.rotate(-12, resample=Image.Resampling.BICUBIC)
    merged = Image.alpha_composite(edited.convert("RGBA"), overlay).convert("RGB")
    merged = Image.alpha_composite(merged.convert("RGBA"), center_banner).convert("RGB")
    return merged.filter(ImageFilter.SHARPEN)


def main() -> None:
    FAKE_DIR.mkdir(parents=True, exist_ok=True)
    generated = []
    for path in sorted(REAL_DIR.iterdir()):
        if not path.is_file() or path.suffix.lower() == ".pdf":
            continue
        with Image.open(path) as image:
            fake = _apply_obvious_tamper(image)
            output = FAKE_DIR / f"{path.stem}_tampered.jpg"
            fake.save(output, format="JPEG", quality=95)
            generated.append(output)

    print(f"Generated {len(generated)} fake artifacts")
    for output in generated:
        print(output)


if __name__ == "__main__":
    main()
