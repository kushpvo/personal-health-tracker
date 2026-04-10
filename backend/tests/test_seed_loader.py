import json

from app.db.models import Biomarker
from app.db.seed_loader import load_biomarkers


def test_seed_loads_biomarkers(test_db):
    load_biomarkers(test_db)
    count = test_db.query(Biomarker).count()
    assert count > 20


def test_seed_is_idempotent(test_db):
    load_biomarkers(test_db)
    first_count = test_db.query(Biomarker).count()
    load_biomarkers(test_db)
    assert test_db.query(Biomarker).count() == first_count


def test_seed_adds_new_entries_to_existing_db(test_db, tmp_path, monkeypatch):
    test_db.add(Biomarker(name="Existing Marker", default_unit="mg/dL"))
    test_db.commit()

    seed = [
        {"name": "Existing Marker", "default_unit": "mg/dL"},
        {"name": "Brand New Marker", "default_unit": "g/L"},
    ]
    seed_file = tmp_path / "biomarkers.json"
    seed_file.write_text(json.dumps(seed))
    monkeypatch.setattr("app.db.seed_loader.SEED_PATH", str(seed_file))

    load_biomarkers(test_db)

    assert test_db.query(Biomarker).count() == 2
    assert (
        test_db.query(Biomarker)
        .filter(Biomarker.name == "Brand New Marker")
        .first()
        is not None
    )
    assert (
        test_db.query(Biomarker)
        .filter(Biomarker.name == "Existing Marker")
        .count()
        == 1
    )


def test_aliases_are_lowercase(test_db):
    load_biomarkers(test_db)
    chol = test_db.query(Biomarker).filter(Biomarker.name == "Total Cholesterol").first()
    assert all(a == a.lower() for a in chol.aliases)
