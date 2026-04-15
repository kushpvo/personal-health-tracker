import json
import os
from sqlalchemy.orm import Session
from app.db.models import Biomarker, ReportResult, Report, User

SEED_PATH = os.path.join(os.path.dirname(__file__), "seed", "biomarkers.json")


def load_biomarkers(db: Session) -> None:
    """Insert new biomarkers and sync existing ones from JSON."""
    with open(SEED_PATH, "r") as f:
        entries = json.load(f)

    existing = {b.name: b for b in db.query(Biomarker).all()}
    added = 0
    updated = 0

    for entry in entries:
        seed_aliases = [a.lower() for a in entry.get("aliases", [])]

        if entry["name"] not in existing:
            db.add(
                Biomarker(
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
                    sex=entry.get("sex"),
                )
            )
            added += 1
        else:
            b = existing[entry["name"]]
            current_aliases = b.aliases or []
            merged_aliases = current_aliases + [
                alias for alias in seed_aliases if alias not in current_aliases
            ]

            changed = False
            if merged_aliases != current_aliases:
                b.aliases = merged_aliases
                changed = True

            for field in (
                "loinc_code",
                "category",
                "description",
                "default_unit",
                "alternate_units",
                "optimal_min",
                "optimal_max",
                "sufficient_min",
                "sufficient_max",
                "unit_conversions",
                "sex",
            ):
                seed_value = entry.get(field)
                if getattr(b, field) != seed_value:
                    setattr(b, field, seed_value)
                    changed = True

            if changed:
                updated += 1

    if added or updated:
        db.commit()
    if added:
        print(f"Seeded {added} new biomarkers.")
    if updated:
        print(f"Updated aliases for {updated} existing biomarkers.")


RETIRED_NEUTRAL = [
    "Testosterone",
    "SHBG",
    "LH",
    "FSH",
    "Estradiol",
    "Progesterone",
    "Prolactin",
    "DHEA-S",
]

DEFAULT_SEX_FOR_RETIRED = {
    "Testosterone": "male",
    "SHBG": "male",
    "LH": "male",
    "FSH": "male",
    "DHEA-S": "male",
    "Estradiol": "female",
    "Progesterone": "female",
    "Prolactin": "female",
}


def migrate_sex_specific_results(db: Session) -> None:
    """
    One-time idempotent migration: re-link ReportResult rows that point to
    retired neutral biomarkers (e.g. 'Testosterone') to sex-specific variants
    (e.g. 'Testosterone (Male)'), then delete the old neutral DB rows.

    Safe to call on every startup — if no retired neutrals exist, it exits immediately.
    """
    for name in RETIRED_NEUTRAL:
        old = (
            db.query(Biomarker)
            .filter(
                Biomarker.name == name,
                Biomarker.sex.is_(None),
            )
            .first()
        )
        if old is None:
            continue

        male_variant = (
            db.query(Biomarker).filter(Biomarker.name == f"{name} (Male)").first()
        )
        female_variant = (
            db.query(Biomarker).filter(Biomarker.name == f"{name} (Female)").first()
        )

        if not male_variant or not female_variant:
            print(
                f"migrate_sex_specific_results: skipping {name} — sex-specific variants not found in DB yet"
            )
            continue

        results = (
            db.query(ReportResult).filter(ReportResult.biomarker_id == old.id).all()
        )
        migrated = 0

        for result in results:
            report = db.query(Report).filter(Report.id == result.report_id).first()
            user_sex = None
            if report:
                user = db.query(User).filter(User.id == report.user_id).first()
                if user:
                    user_sex = user.sex

            default_sex = DEFAULT_SEX_FOR_RETIRED[name]
            chosen_sex = user_sex if user_sex in ("male", "female") else default_sex
            chosen_variant = male_variant if chosen_sex == "male" else female_variant
            result.biomarker_id = chosen_variant.id
            migrated += 1

        db.flush()
        db.query(Biomarker).filter(Biomarker.id == old.id).delete(
            synchronize_session=False
        )
        db.flush()
        print(
            f"migrate_sex_specific_results: migrated {migrated} results for '{name}', deleted old neutral row"
        )

    db.commit()
