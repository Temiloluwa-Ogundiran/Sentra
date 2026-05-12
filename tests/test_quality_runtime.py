from PIL import Image, ImageDraw

from app.inference.quality import assess_quality


def test_assess_quality_flags_obvious_red_edit_overlay(tmp_path):
    path = tmp_path / "tampered.jpg"
    image = Image.new("RGB", (600, 1000), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((100, 100, 500, 240), fill=(220, 20, 20))
    image.save(path)

    flags = assess_quality(path)

    assert "edited_overlay_signal" in flags
