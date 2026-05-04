import pytest
from app.services.parser import extract_biomarkers, extract_metadata, ParsedResult


SAMPLE_LABCORP = """
PATIENT: John Doe
COLLECTION DATE: 03/15/2025
PHYSICIAN: Dr. Smith

TEST NAME               RESULT      FLAG    UNITS       REFERENCE INTERVAL
Glucose                 87                  mg/dL       65-99
Urea Nitrogen (BUN)     14                  mg/dL       7-25
Creatinine              0.93                mg/dL       0.70-1.33
Total Cholesterol       183                 mg/dL       100-199
HDL Cholesterol         62                  mg/dL       >40
LDL Cholesterol         98                  mg/dL       0-99
Triglycerides           115                 mg/dL       0-149
TSH                     2.15                mIU/L       0.40-4.50
"""

SAMPLE_QUEST = """
Quest Diagnostics
Date of Service: April 2, 2025

Component              Your Value    Standard Range
GLUCOSE                94 mg/dL      65-99 mg/dL
HEMOGLOBIN A1c         5.4 %         <5.7 %
VITAMIN D, 25-OH       38 ng/mL      30-100 ng/mL
FERRITIN               45 ng/mL      12-300 ng/mL
"""


def test_extract_metadata_labcorp_date():
    meta = extract_metadata(SAMPLE_LABCORP)
    assert meta["sample_date"] is not None
    assert meta["sample_date"].month == 3
    assert meta["sample_date"].day == 15
    assert meta["sample_date"].year == 2025


def test_extract_metadata_quest_date():
    meta = extract_metadata(SAMPLE_QUEST)
    assert meta["sample_date"] is not None
    assert meta["sample_date"].month == 4
    assert meta["sample_date"].day == 2


def test_extract_biomarkers_labcorp():
    results = extract_biomarkers(SAMPLE_LABCORP)
    names = {r.raw_name.lower() for r in results}
    assert "glucose" in names
    assert "total cholesterol" in names
    assert "tsh" in names


def test_extract_biomarker_values_labcorp():
    results = extract_biomarkers(SAMPLE_LABCORP)
    glucose = next(r for r in results if "glucose" in r.raw_name.lower())
    assert glucose.value == pytest.approx(87.0)
    assert glucose.unit == "mg/dL"


def test_extract_biomarkers_quest():
    results = extract_biomarkers(SAMPLE_QUEST)
    names = {r.raw_name.lower() for r in results}
    assert "glucose" in names


def test_no_false_positives_on_headers():
    results = extract_biomarkers(SAMPLE_LABCORP)
    raw_names = [r.raw_name for r in results]
    assert not any("TEST NAME" in n for n in raw_names)
    assert not any("PATIENT" in n for n in raw_names)


def test_extract_biomarkers_handles_single_space_lab_rows():
    text = """
    Haemoglobin 143 ( 130-170 ) g/L
    Glucose (Non-Fasting) 4.6 - mmol/L
    Total Cholesterol 5.6 H ( < 5.0 ) mmol/L
    Vitamin D (25-0OH) 68 nmol/L
    """

    results = extract_biomarkers(text)

    assert len(results) == 4
    assert results[0].raw_name == "Haemoglobin"
    assert results[0].value == 143.0
    assert results[0].unit == "g/L"
    assert results[1].raw_name == "Glucose (Non-Fasting)"
    assert results[1].unit == "mmol/L"
    assert results[2].raw_name == "Total Cholesterol"
    assert results[2].value == 5.6
    assert results[3].raw_name == "Vitamin D (25-0OH)"


SAMPLE_MEDDBASE = """
' Haemoglobin ' 142 | g/L ! (130-170) 1 !
' Haematocrit ' 0.44 | L/L ! (0.40-0.54) 1 !
' RDW ' 12.7 1 % ' (11.6-14.0) 1 !
' TSH ' 13.80 ' mIU/L ' (0.27-4.20) 'HH
' Vitamin D ' 76 ' nmol/L ' (50-175) 1
| MCH ; 30.5 | Pg | (27-32) ' '
' Platelets 1 382 ' x10e9/L ! (150-410) H H
! Neutrophils ' 3.9 ' x10e9/L ! (2.0-7.0) ! !
! Total Protein 1 77 ' g/L ' (60-80) ! !
‘ Total Bilirubin | 6 ' umol/L ' (<21) H H
' Albumin : 50 | B/L 1 (35-50) ! !
' Globulins | 27 | B/L 1 (20-40)
! Triglycerides ' 1.9 ' mmol/L ' (< 1.70) 'H \\
| Glucose (Non-Fasting) | 4,3 + mmol/L + ' '
' Calcium 1 2.53 ' mmol/L 1 (2,10-2.55) ! !
"""


def test_extract_biomarkers_meddbase_format():
    results = extract_biomarkers(SAMPLE_MEDDBASE)
    by_name = {r.raw_name.lower(): r for r in results}

    assert "haemoglobin" in by_name
    assert by_name["haemoglobin"].value == pytest.approx(142.0)
    assert by_name["haemoglobin"].unit == "g/L"

    assert "rdw" in by_name
    assert by_name["rdw"].value == pytest.approx(12.7)
    assert by_name["rdw"].unit == "%"

    assert "globulins" in by_name
    assert by_name["globulins"].value == pytest.approx(27.0)
    assert by_name["globulins"].unit == "g/L"

    assert "tsh" in by_name
    assert by_name["tsh"].value == pytest.approx(13.80)
    assert by_name["tsh"].unit == "mIU/L"

    assert "vitamin d" in by_name
    assert by_name["vitamin d"].value == pytest.approx(76.0)

    assert "mch" in by_name
    assert by_name["mch"].value == pytest.approx(30.5)
    assert by_name["mch"].unit == "pg"

    assert "platelets" in by_name
    assert by_name["platelets"].value == pytest.approx(382.0)

    assert "neutrophils" in by_name
    assert by_name["neutrophils"].value == pytest.approx(3.9)

    assert "total protein" in by_name
    assert by_name["total protein"].value == pytest.approx(77.0)
    assert by_name["total protein"].unit == "g/L"

    assert "total bilirubin" in by_name
    assert by_name["total bilirubin"].value == pytest.approx(6.0)
    assert by_name["total bilirubin"].unit == "umol/L"

    assert "albumin" in by_name
    assert by_name["albumin"].value == pytest.approx(50.0)
    assert by_name["albumin"].unit == "g/L"

    assert "globulins" in by_name
    assert by_name["globulins"].value == pytest.approx(27.0)
    assert by_name["globulins"].unit == "g/L"

    assert "triglycerides" in by_name
    assert by_name["triglycerides"].value == pytest.approx(1.9)

    assert "glucose (non-fasting)" in by_name
    assert by_name["glucose (non-fasting)"].value == pytest.approx(4.3)

    assert "calcium" in by_name
    assert by_name["calcium"].value == pytest.approx(2.53)


def test_extract_biomarkers_normalizes_common_ocr_unit_errors():
    text = """
    MCV 94.4 ( 81-101 ) £L
    Platelets 419 H ( 150-410 ) xl0e9/L
    MCH 30.1 ( 27-34 ) fH
    """

    results = extract_biomarkers(text)

    assert len(results) == 3
    assert results[0].unit == "fL"
    assert results[1].unit == "x10e9/L"
    assert results[2].unit == "fL"
