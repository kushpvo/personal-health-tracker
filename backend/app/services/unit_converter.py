from typing import List, Optional, Tuple
from app.db.models import Biomarker, ReportResult


def normalize_unit(unit: str) -> str:
    """Normalize unit string: strip whitespace, replace µ/μ with u."""
    unit = unit.strip()
    unit = unit.replace("µ", "u").replace("μ", "u")
    return unit


def _get_conversion_factor(conversion_entry) -> Tuple[float, float]:
    """Extract factor and offset from a conversion entry.

    Supports:
    - numeric factor: 88.57  -> (88.57, 0)
    - dict: {"factor": 10.929, "offset": -2.15} -> (10.929, -2.15)
    """
    if isinstance(conversion_entry, dict):
        return float(conversion_entry.get("factor", 1)), float(conversion_entry.get("offset", 0))
    return float(conversion_entry), 0.0


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
    entry = factors.get(default_unit)

    if entry is not None:
        factor, offset = _get_conversion_factor(entry)
        return value * factor + offset, default_unit

    # No conversion available — return original
    return value, extracted_unit


def pick_best_result(group: List[ReportResult], biomarker: Biomarker) -> Optional[ReportResult]:
    """Choose the best result when a report has multiple rows for the same biomarker."""
    if len(group) == 1:
        return group[0]

    default_unit = normalize_unit(biomarker.default_unit or "")

    # Prefer results already in default unit
    for r in group:
        if normalize_unit(r.unit) == default_unit:
            return r

    # Prefer results that can be converted to default unit
    conversions = biomarker.unit_conversions or {}
    for r in group:
        factors = conversions.get(normalize_unit(r.unit), {})
        target = factors.get(default_unit)
        if target is not None:
            return r

    return group[0]
