from datetime import datetime, timezone

from app.db.seed_loader import load_biomarkers, migrate_sex_specific_results
from app.db.models import Biomarker, Report, ReportResult
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


def test_match_biomarker_uses_default_variant_for_other_sex(test_db):
    load_biomarkers(test_db)

    testosterone = _match_biomarker("Testosterone", test_db, user_sex="other")
    estradiol = _match_biomarker("Estradiol", test_db, user_sex="other")

    assert testosterone is not None
    assert testosterone.name == "Testosterone (Male)"
    assert estradiol is not None
    assert estradiol.name == "Estradiol (Female)"


def test_load_biomarkers_syncs_existing_metadata(test_db):
    biomarker = Biomarker(
        name="ESR",
        aliases=["esr"],
        category="Inflammatory",
        description="old",
        default_unit="mm/Hour",
        alternate_units=[],
        optimal_min=0,
        optimal_max=1,
        sufficient_min=0,
        sufficient_max=2,
        unit_conversions={},
        sex=None,
    )
    test_db.add(biomarker)
    test_db.commit()

    load_biomarkers(test_db)
    test_db.refresh(biomarker)

    assert biomarker.category == "Inflammation"
    assert biomarker.description != "old"


def test_migrate_sex_specific_results_handles_retired_biomarker_without_results(
    test_db,
):
    load_biomarkers(test_db)

    retired = Biomarker(
        name="Testosterone",
        loinc_code="2986-8",
        aliases=["testosterone"],
        category="Hormones",
        description="retired",
        default_unit="ng/dL",
        alternate_units=["nmol/L"],
        optimal_min=600,
        optimal_max=900,
        sufficient_min=350,
        sufficient_max=1000,
        unit_conversions={},
        sex=None,
    )
    test_db.add(retired)
    test_db.commit()

    migrate_sex_specific_results(test_db)

    assert (
        test_db.query(Biomarker)
        .filter(Biomarker.name == "Testosterone", Biomarker.sex.is_(None))
        .first()
        is None
    )


def test_migrate_sex_specific_results_relinks_existing_results(test_db, create_user):
    load_biomarkers(test_db)
    user = create_user()
    user.sex = "female"
    test_db.commit()

    retired = Biomarker(
        name="Estradiol",
        loinc_code="2243-4",
        aliases=["estradiol"],
        category="Hormones",
        description="retired",
        default_unit="pmol/L",
        alternate_units=["pg/mL"],
        optimal_min=0,
        optimal_max=1,
        sufficient_min=0,
        sufficient_max=2,
        unit_conversions={},
        sex=None,
    )
    test_db.add(retired)
    test_db.commit()
    test_db.refresh(retired)

    report = Report(
        filename="estradiol.txt",
        original_filename="estradiol.txt",
        file_path="/dev/null",
        status="done",
        uploaded_at=datetime.now(timezone.utc),
        user_id=user.id,
    )
    test_db.add(report)
    test_db.commit()
    test_db.refresh(report)

    result = ReportResult(
        report_id=report.id,
        biomarker_id=retired.id,
        raw_name="Estradiol",
        value=123,
        unit="pmol/L",
        is_flagged_unknown=False,
    )
    test_db.add(result)
    test_db.commit()

    migrate_sex_specific_results(test_db)
    test_db.refresh(result)

    biomarker = (
        test_db.query(Biomarker).filter(Biomarker.id == result.biomarker_id).first()
    )
    assert biomarker is not None
    assert biomarker.name == "Estradiol (Female)"
