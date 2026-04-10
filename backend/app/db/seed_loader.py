import json
import os
from sqlalchemy.orm import Session
from app.db.models import Biomarker

SEED_PATH = os.path.join(os.path.dirname(__file__), "seed", "biomarkers.json")


def load_biomarkers(db: Session) -> None:
    """Insert new biomarkers and sync aliases for existing ones from JSON."""
    with open(SEED_PATH, "r") as f:
        entries = json.load(f)

    existing = {b.name: b for b in db.query(Biomarker).all()}
    added = 0
    updated = 0

    for entry in entries:
        seed_aliases = [a.lower() for a in entry.get("aliases", [])]

        if entry["name"] not in existing:
            db.add(Biomarker(
                name=entry["name"],
                loinc_code=entry.get("loinc_code"),
                aliases=seed_aliases,
                category=entry.get("category"),
                description=entry.get("description"),
                default_unit=entry.get("default_unit"),
                alternate_units=entry.get("alternate_units", []),
                optimal_min=entry.get("optimal_min"),
                optimal_max=entry.get("optimal_max"),
                sufficient_min=entry.get("sufficient_min"),
                sufficient_max=entry.get("sufficient_max"),
                unit_conversions=entry.get("unit_conversions", {}),
            ))
            added += 1
        else:
            # Sync aliases: add any new ones from the seed without removing manual additions
            b = existing[entry["name"]]
            current = set(b.aliases or [])
            new_aliases = [a for a in seed_aliases if a not in current]
            if new_aliases:
                b.aliases = list(current) + new_aliases
                updated += 1

    if added or updated:
        db.commit()
    if added:
        print(f"Seeded {added} new biomarkers.")
    if updated:
        print(f"Updated aliases for {updated} existing biomarkers.")
