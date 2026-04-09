import pytest
from app.db.models import Biomarker
from app.services.unit_converter import convert_to_default_unit, normalize_unit


def make_biomarker(**kwargs) -> Biomarker:
    defaults = dict(
        name="Test",
        default_unit="mg/dL",
        alternate_units=["mmol/L"],
        unit_conversions={"mg/dL": {"mmol/L": 0.02586}, "mmol/L": {"mg/dL": 38.67}},
    )
    defaults.update(kwargs)
    b = Biomarker()
    for k, v in defaults.items():
        setattr(b, k, v)
    return b


def test_no_conversion_needed():
    b = make_biomarker()
    value, unit = convert_to_default_unit(180.0, "mg/dL", b)
    assert unit == "mg/dL"
    assert value == pytest.approx(180.0)


def test_converts_mmol_to_mg():
    b = make_biomarker()
    value, unit = convert_to_default_unit(4.65, "mmol/L", b)
    assert unit == "mg/dL"
    assert value == pytest.approx(179.8, abs=0.5)


def test_unknown_unit_returns_original():
    b = make_biomarker()
    value, unit = convert_to_default_unit(99.0, "foobar", b)
    assert unit == "foobar"
    assert value == pytest.approx(99.0)


def test_normalize_unit_strips_whitespace():
    assert normalize_unit("  mg/dL  ") == "mg/dL"


def test_normalize_unit_micro_symbol():
    assert normalize_unit("µmol/L") == "umol/L"
    assert normalize_unit("μmol/L") == "umol/L"


def test_normalize_unit_case_preserved():
    assert normalize_unit("ng/mL") == "ng/mL"
