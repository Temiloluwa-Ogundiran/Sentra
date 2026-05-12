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


def test_assess_quality_flags_green_marker_over_amount_region(tmp_path):
    path = tmp_path / "tampered_green.jpg"
    image = Image.new("RGB", (720, 1280), "white")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((80, 180, 640, 1040), radius=24, fill=(250, 250, 250))
    draw.text((120, 260), "N10,000.00", fill=(20, 20, 20))
    draw.line((280, 250, 330, 360), fill=(40, 255, 160), width=26)
    draw.line((330, 250, 280, 360), fill=(40, 255, 160), width=26)
    image.save(path)

    flags = assess_quality(path)

    assert "edited_overlay_signal" in flags


def test_assess_quality_flags_reference_clone_signal(monkeypatch, tmp_path):
    reference_dir = tmp_path / "real"
    reference_dir.mkdir()

    reference_path = reference_dir / "reference.jpg"
    reference = Image.new("RGB", (540, 960), "#1155dd")
    reference_draw = ImageDraw.Draw(reference)
    reference_draw.rounded_rectangle((40, 120, 500, 760), radius=24, fill="white")
    reference_draw.text((70, 170), "N10,000.00", fill="black")
    reference_draw.text((70, 260), "REF123456789", fill="black")
    reference.save(reference_path)

    candidate_path = tmp_path / "candidate.jpg"
    candidate = reference.copy()
    candidate_draw = ImageDraw.Draw(candidate)
    candidate_draw.rectangle((70, 170, 260, 220), fill="white")
    candidate_draw.text((70, 170), "N20,000.00", fill="black")
    candidate.save(candidate_path)

    monkeypatch.setattr("app.inference.quality.REFERENCE_REAL_DIR", reference_dir)
    monkeypatch.setattr("app.inference.quality._REFERENCE_CACHE", {})

    flags = assess_quality(candidate_path)

    assert "reference_clone_signal" in flags
