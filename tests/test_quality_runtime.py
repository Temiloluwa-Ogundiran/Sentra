from pathlib import Path

from PIL import Image, ImageDraw

from app.inference.quality import assess_quality, find_visible_edit_regions


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


def test_assess_quality_flags_green_marker_outside_amount_region(tmp_path):
    path = tmp_path / "tampered_notes.jpg"
    image = Image.new("RGB", (720, 1280), "white")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((80, 180, 640, 1040), radius=24, fill=(250, 250, 250))
    draw.text((120, 260), "N10,000.00", fill=(20, 20, 20))
    draw.text((120, 620), "TEMILOLUWA SAMUEL OGUNDIRAN", fill=(20, 20, 20))
    draw.line((430, 640, 520, 630), fill=(40, 255, 160), width=20)
    draw.line((250, 900, 270, 980), fill=(40, 255, 160), width=20)
    image.save(path)

    flags = assess_quality(path)
    regions = find_visible_edit_regions(path)

    assert "edited_overlay_signal" in flags
    assert len(regions) >= 2


def test_assess_quality_ignores_square_green_ui_elements(tmp_path):
    path = tmp_path / "legit_green_ui.jpg"
    image = Image.new("RGB", (720, 1280), "white")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((80, 180, 640, 1040), radius=24, fill=(250, 250, 250))
    draw.rounded_rectangle((100, 260, 150, 310), radius=8, fill=(40, 220, 140))
    draw.rounded_rectangle((260, 250, 320, 320), radius=10, fill=(40, 220, 140))
    image.save(path)

    flags = assess_quality(path)
    regions = find_visible_edit_regions(path)

    assert "edited_overlay_signal" not in flags
    assert regions == []


def test_assess_quality_flags_reference_clone_signal(monkeypatch, tmp_path):
    path = tmp_path / "candidate.jpg"
    Image.new("RGB", (540, 960), "#1155dd").save(path)
    monkeypatch.setattr("app.inference.quality._find_reference_match", lambda file_path, image: ("clone", None))

    flags = assess_quality(path)

    assert "reference_clone_signal" in flags


def test_assess_quality_flags_reference_template_match(monkeypatch, tmp_path):
    reference_dir = tmp_path / "real"
    reference_dir.mkdir()
    manifest_path = tmp_path / "reference_manifest.json"

    reference_path = reference_dir / "reference.jpg"
    reference = Image.new("RGB", (540, 960), "#1155dd")
    reference_draw = ImageDraw.Draw(reference)
    reference_draw.rounded_rectangle((40, 120, 500, 760), radius=24, fill="white")
    reference_draw.text((70, 170), "N10,000.00", fill="black")
    reference_draw.text((70, 260), "REF123456789", fill="black")
    reference.save(reference_path)
    manifest_path.write_text(
        '{"reference.jpg":{"amount":"N10,000.00","currency":"NGN","reference":"REF123456789"}}',
        encoding="utf-8",
    )

    monkeypatch.setattr("app.inference.quality.REFERENCE_REAL_DIR", reference_dir)
    monkeypatch.setattr("app.inference.quality.REFERENCE_MANIFEST_PATH", manifest_path)
    monkeypatch.setattr("app.inference.quality._REFERENCE_CACHE", {})

    flags = assess_quality(reference_path)

    assert "reference_template_match" in flags


def test_assess_quality_flags_synthetic_render_signal(monkeypatch):
    sample_path = Path("tests/fixtures/ai_generated_moniepoint_clone.png")
    monkeypatch.setattr("app.inference.quality._find_reference_match", lambda file_path, image: None)

    flags = assess_quality(sample_path)

    assert "synthetic_render_signal" in flags
