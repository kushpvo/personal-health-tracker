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
