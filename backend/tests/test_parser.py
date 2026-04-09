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
