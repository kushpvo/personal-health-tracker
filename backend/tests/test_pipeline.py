from app.db.seed_loader import load_biomarkers
from app.services.pipeline import _match_biomarker


def test_match_biomarker_strips_qualifiers(test_db):
    load_biomarkers(test_db)

    glucose = _match_biomarker("Glucose (Non-Fasting)", test_db)
    vitamin_d = _match_biomarker("Vitamin D (25-0OH)", test_db)

    assert glucose is not None
    assert glucose.name == "Glucose"
    assert vitamin_d is not None
    assert vitamin_d.name == "Vitamin D"


def test_newly_seeded_markers_all_match(test_db):
    load_biomarkers(test_db)
    for name in [
        # CBC
        "Haematocrit",
        "RBC",
        "MCV",
        "MCH",
        "MCHC",
        "RDW",
        "Platelets",
        "MPV",
        "Neutrophils",
        "Lymphocytes",
        "Monocytes",
        "Eosinophils",
        "Basophils",
        "ESR",
        # Liver
        "Total Bilirubin",
        "ALP",
        "GGT",
        "Albumin",
        "Globulins",
        "Total Protein",
        "Aspartate Transferase",
        # Metabolic / electrolytes
        "Urea",
        "Calcium",
        "Adjusted Calcium",
        "Phosphate",
        "Urate",
        "Sodium",
        "Potassium",
        "Chloride",
        "Bicarbonate",
        "Magnesium",
        # Iron
        "Iron",
        "UIBC",
        "TIBC",
        "Transferrin",
        "Transferrin Saturation",
    ]:
        result = _match_biomarker(name, test_db)
        assert result is not None, f"Expected {name!r} to match a biomarker"


def test_newly_seeded_markers_match_by_alias(test_db):
    """Verify key alias lookups that are likely to appear in OCR text."""
    load_biomarkers(test_db)
    alias_cases = [
        ("BUN", "Urea"),
        ("Alkaline Phosphatase", "ALP"),
        ("Gamma GT", "GGT"),
        ("Aspartate Transferase", "AST"),
        ("hs-CRP", "HsCRP"),
    ]
    for alias, expected_name in alias_cases:
        result = _match_biomarker(alias, test_db)
        assert result is not None, f"Alias {alias!r} matched nothing"
        assert result.name == expected_name, (
            f"Alias {alias!r}: expected {expected_name!r}, got {result.name!r}"
        )


def test_pipeline_sets_sort_order(test_db, create_user):
    """sort_order on saved results must match OCR extraction order."""
    from app.db.models import ReportResult
    from datetime import datetime, timezone
    from app.db.models import Report

    load_biomarkers(test_db)
    user = create_user()

    report = Report(
        filename="sort_test.txt",
        original_filename="sort_test.txt",
        file_path="/dev/null",
        status="pending",
        uploaded_at=datetime.now(timezone.utc),
        user_id=user.id,
    )
    test_db.add(report)
    test_db.commit()
    test_db.refresh(report)

    from app.services.pipeline import run_pipeline
    from unittest.mock import patch

    fake_ocr_text = (
        "Glucose                 90          mg/dL\n"
        "Total Cholesterol       180         mg/dL\n"
        "TSH                     2.1         mIU/L\n"
    )

    with patch("app.services.pipeline._get_ocr_backend") as mock_backend:
        mock_backend.return_value.extract_text.return_value = fake_ocr_text
        with patch("app.services.pipeline.prepare_images") as mock_prep:
            mock_prep.return_value = ["/fake/image.png"]
            run_pipeline(report.id, test_db)

    results = (
        test_db.query(ReportResult)
        .filter(ReportResult.report_id == report.id)
        .order_by(ReportResult.sort_order)
        .all()
    )

    assert len(results) == 3
    assert [r.sort_order for r in results] == [0, 1, 2]
    assert results[0].raw_name == "Glucose"
    assert results[1].raw_name == "Total Cholesterol"
    assert results[2].raw_name == "TSH"
