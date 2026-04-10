from pathlib import Path

import pytest
import pdf2image
from pdf2image.exceptions import PDFInfoNotInstalledError

from app.services.preprocessor import prepare_images


def test_prepare_images_reports_missing_poppler(monkeypatch, tmp_path):
    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    def fake_convert_from_path(*args, **kwargs):
        raise PDFInfoNotInstalledError("missing pdfinfo")

    monkeypatch.setattr(pdf2image, "convert_from_path", fake_convert_from_path)

    with pytest.raises(RuntimeError, match="Poppler is required to process PDF uploads"):
        prepare_images(str(pdf_path))
