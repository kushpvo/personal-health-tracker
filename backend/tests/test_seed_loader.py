from app.db.models import Biomarker
from app.db.seed_loader import load_biomarkers


def test_seed_loads_biomarkers(test_db):
    load_biomarkers(test_db)
    count = test_db.query(Biomarker).count()
    assert count == 20


def test_seed_is_idempotent(test_db):
    load_biomarkers(test_db)
    load_biomarkers(test_db)  # second call should be a no-op
    count = test_db.query(Biomarker).count()
    assert count == 20


def test_aliases_are_lowercase(test_db):
    load_biomarkers(test_db)
    chol = test_db.query(Biomarker).filter(Biomarker.name == "Total Cholesterol").first()
    assert all(a == a.lower() for a in chol.aliases)
