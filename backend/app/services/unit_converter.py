from typing import Tuple
from app.db.models import Biomarker


def normalize_unit(unit: str) -> str:
    """Normalize unit string: strip whitespace, replace µ/μ with u."""
    unit = unit.strip()
    unit = unit.replace("µ", "u").replace("μ", "u")
    return unit


def convert_to_default_unit(
    value: float, extracted_unit: str, biomarker: Biomarker
) -> Tuple[float, str]:
    """
    Convert value to biomarker's default_unit if a conversion factor exists.
    Returns (converted_value, unit_used).
    If no conversion is found, returns (original_value, extracted_unit).
    """
    extracted_unit = normalize_unit(extracted_unit)
    default_unit = normalize_unit(biomarker.default_unit or "")

    if extracted_unit == default_unit:
        return value, extracted_unit

    conversions = biomarker.unit_conversions or {}
    factors = conversions.get(extracted_unit, {})
    factor = factors.get(default_unit)

    if factor is not None:
        return value * factor, default_unit

    # No conversion available — return original
    return value, extracted_unit
