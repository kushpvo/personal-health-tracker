import json
import os
from sqlalchemy.orm import Session
from app.db.models import Biomarker

SEED_PATH = os.path.join(os.path.dirname(__file__), "seed", "biomarkers.json")


def load_biomarkers(db: Session) -> None:
    """Load biomarkers from JSON into DB if the table is empty."""
    if db.query(Biomarker).count() > 0:
        return

    with open(SEED_PATH, "r") as f:
        entries = json.load(f)

    for entry in entries:
        biomarker = Biomarker(
            name=entry["name"],
            loinc_code=entry.get("loinc_code"),
            aliases=[a.lower() for a in entry.get("aliases", [])],
            category=entry.get("category"),
            description=entry.get("description"),
            default_unit=entry.get("default_unit"),
            alternate_units=entry.get("alternate_units", []),
            optimal_min=entry.get("optimal_min"),
            optimal_max=entry.get("optimal_max"),
            sufficient_min=entry.get("sufficient_min"),
            sufficient_max=entry.get("sufficient_max"),
            unit_conversions=entry.get("unit_conversions", {}),
        )
        db.add(biomarker)

    db.commit()
    print(f"Seeded {len(entries)} biomarkers.")
