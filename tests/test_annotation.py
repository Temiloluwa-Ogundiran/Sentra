from pathlib import Path

import fitz
from PIL import Image

from app.inference.annotate import annotate_artifact


def test_annotate_artifact_renders_pdf_preview(monkeypatch, tmp_path):
    monkeypatch.setattr("app.inference.annotate.settings.storage_root", tmp_path)
    pdf_path = tmp_path / "proof.pdf"

    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Sentra PDF proof")
    document.save(pdf_path)
    document.close()

    output = annotate_artifact(pdf_path, "receipt_pdf_render", ["Reference mismatch"], 7)

    assert output.exists()
    with Image.open(output) as rendered:
        assert rendered.width > 0
        assert rendered.height > 0
