import fitz

from app.inference.ocr import run_ocr
from app.inference.quality import assess_quality


def test_pdf_ocr_extracts_text_layer_fields(tmp_path):
    pdf_path = tmp_path / "quickteller.pdf"
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text(
        (50, 80),
        "\n".join(
            [
                "Your Transaction was Successful",
                "Amount / Surcharge",
                "₦ 500.00 / ₦ 100.00",
                "Transaction Date",
                "2026-05-12 10:08 AM",
                "Customer Name",
                "OGUNDIRAN GBENGA SOLOMON",
                "Bank",
                "Zenith Bank International",
                "Payment Reference",
                "ZIB|Web|3QTI0001|IEPP|120526100851|N9WP",
            ]
        ),
    )
    document.save(pdf_path)
    document.close()

    raw_text, fields = run_ocr(pdf_path)

    assert "Transaction was Successful" in raw_text
    assert fields.amount == "500.00"
    assert fields.currency == "NGN"
    assert fields.date == "2026-05-12"
    assert fields.time == "10:08 AM"
    assert fields.provider == "Zenith Bank International"
    assert fields.recipient_label == "OGUNDIRAN GBENGA SOLOMON"
    assert fields.reference == "ZIB|Web|3QTI0001|IEPP|120526100851|N9WP"


def test_pdf_quality_uses_page_dimensions(tmp_path):
    pdf_path = tmp_path / "receipt.pdf"
    document = fitz.open()
    document.new_page(width=595, height=842)
    document.save(pdf_path)
    document.close()

    assert assess_quality(pdf_path) == []
