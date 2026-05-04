import re
from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Dict, Any

from dateutil import parser as dateutil_parser


@dataclass
class ParsedResult:
    raw_name: str
    value: float
    unit: str


# Lines that are definitely headers, not biomarker rows
SKIP_PATTERNS = re.compile(
    r"^(test name|component|your value|standard range|reference|patient|physician|"
    r"collected|collection|date|lab|page|report|specimen|flag|result|units?|"
    r"normal|abnormal|critical|high|low|see note|footnote|\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)

# Matches: <name> <numeric_value> <unit>  (column-separated with 2+ spaces)
BIOMARKER_LINE = re.compile(
    r"^([A-Za-z][A-Za-z0-9\s,\(\)/\-\.%]+?)"
    r"\s{2,}"
    r"([<>]?\s*\d+\.?\d*)"
    r"\s+"
    r"([A-Za-z%µu][A-Za-z0-9/%µu·\^\-]*)"
    r"(?:\s+.*)?$",
    re.IGNORECASE,
)

# Quest-style: NAME  VALUE UNIT  (unit attached to value, single space)
BIOMARKER_INLINE_UNIT = re.compile(
    r"^([A-Za-z][A-Za-z0-9\s,\(\)/\-\.%]+?)"
    r"\s{2,}"
    r"([<>]?\s*\d+\.?\d*)\s*([A-Za-z%][A-Za-z0-9/%µu·\^\-]*)",
    re.IGNORECASE,
)

# Meddbase patient portal format: NAME VALUE UNIT (RANGE) [FLAG]
# e.g. "Haemoglobin 142 g/L (130-170) 1"  or  "TSH 13.80 mIU/L (0.27-4.20) HH"
BIOMARKER_WITH_PAREN_RANGE = re.compile(
    r"^(?P<name>[A-Za-z][A-Za-z0-9\s,\(\)/\-.%]+?)"
    r"\s+"
    r"(?P<value>[<>]?\s*\d+\.?\d*)"
    r"\s+"
    r"(?P<unit>[A-Za-z%µu£][A-Za-z0-9/%µu·\^\-]*)"
    r"\s+"
    r"\([<>]?\s*\d*\.?\d+\s*(?:[-–]\s*[<>]?\s*\d*\.?\d+)?\)"
    r"(?:\s+\S+)*"
    r"\s*$",
    re.IGNORECASE,
)

# Table-cell delimiter lines from Meddbase-style PDFs start with ' | ! or Unicode left-quote
_TABLE_DELIM_LINE = re.compile(r"^['‘\|!]")
_TABLE_DELIMS = re.compile(r"['‘\|!:;+]")

DATE_LABEL_PATTERNS = [
    re.compile(
        r"(?:collection date|date of service|date collected|specimen date|"
        r"report date|drawn|collected)[:\s]+(.+)",
        re.IGNORECASE,
    ),
]

BARE_DATE_PATTERNS = [
    re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b"),
    re.compile(r"\b([A-Z][a-z]+ \d{1,2},? \d{4})\b"),
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
]

# Handles: NAME VALUE UNIT REF_LOW - REF_HIGH [FLAG]
# e.g. "RED CELL COUNT 4.38 x10^12/L 4.40 - 5.80 L"
# Matches before SINGLE_SPACE_WITH_RANGE so the reference range and flag
# are never mistaken for the actual value and unit.
BIOMARKER_WITH_RANGE_FLAG = re.compile(
    r"^(?P<name>[A-Za-z][A-Za-z0-9\s,\(\)/\-.%]+?)"
    r"\s+"
    r"(?P<value>[<>]?\s*\d+\.?\d*)"
    r"\s+"
    r"(?P<unit>[A-Za-z%µu£][A-Za-z0-9/%µu·\^\-]*)"
    r"\s+"
    r"[<>]?\d+\.?\d*\s*[-–]\s*[<>]?\d+\.?\d*"   # reference range: N - N
    r"(?:\s+(?:H{1,2}|L{1,2}|N))?"               # optional result flag
    r"\s*$",
    re.IGNORECASE,
)

SINGLE_SPACE_WITH_RANGE = re.compile(
    r"^"
    r"(?P<name>[A-Za-z][A-Za-z0-9\s,\(\)/\-.%]+?)"
    r"\s+"
    r"(?P<value>[<>]?\s*\d+\.?\d*)"
    r"\s+"
    r"(?:(?P<flag>H|L|HH|LL|-)\s+)?"
    r"(?:[\(\{\|]\s*[^)]*?[)\}]?\s+)?"
    r"(?P<unit>[A-Za-z%µu£][A-Za-z0-9/%µu·\^\-]*)"
    r"\s*$",
    re.IGNORECASE,
)

# Single-letter result flags that are never valid measurement units
_RESULT_FLAGS = re.compile(r"^(H{1,2}|L{1,2}|N)$", re.IGNORECASE)


def _normalize_ocr_unit(raw_unit: str) -> str:
    unit = raw_unit.strip()
    unit = unit.replace("£", "f")
    unit = unit.replace("xl0", "x10")
    # OCR reads superscript exponent marker: x10^9/L → x1049/L (^ read as 4)
    unit = re.sub(r"x104(\d)", r"x10^\1", unit)
    # OCR misreads 'L' as 'H': fH → fL (femtoliters)
    unit = unit.replace("fH", "fL")
    # OCR misreads 'g' as 'B': B/L → g/L (grams per litre)
    unit = unit.replace("B/L", "g/L")
    # OCR capitalises picogram: Pg → pg
    unit = unit.replace("Pg", "pg")
    return unit


def _normalize_table_line(line: str) -> str:
    """Strip Meddbase-style table cell delimiters (' | ! :) so rows parse cleanly."""
    if not _TABLE_DELIM_LINE.match(line):
        return line
    normalized = _TABLE_DELIMS.sub(" ", line)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    # Strip trailing punctuation/backslash artifacts left after delimiter removal
    normalized = normalized.rstrip(" .,\\")
    # OCR misreads '!' as '1'; remove spurious '1' between value and unit or before range paren.
    normalized = re.sub(r"(\d+\.?\d*) 1 ([A-Za-z%])", r"\1 \2", normalized)
    normalized = re.sub(r" 1 \(", " (", normalized)
    # Normalize European decimal commas in values and range bounds (e.g. 4,3 → 4.3)
    normalized = re.sub(r"(\d),(\d)", r"\1.\2", normalized)
    return normalized


# Trailing differential percentage: "Neutrophils 49.2%" → "Neutrophils"
_TRAILING_PCT = re.compile(r"\s+\d+\.?\d*%\s*$")


def _parse_value(raw: str) -> Optional[float]:
    raw = raw.strip().lstrip("<>").strip()
    try:
        return float(raw)
    except ValueError:
        return None


def extract_metadata(text: str) -> Dict[str, Any]:
    sample_date: Optional[date] = None

    for line in text.splitlines():
        for pattern in DATE_LABEL_PATTERNS:
            m = pattern.search(line)
            if m:
                try:
                    sample_date = dateutil_parser.parse(m.group(1).strip(), fuzzy=True).date()
                    break
                except Exception:
                    pass
        if sample_date:
            break

    if not sample_date:
        for pattern in BARE_DATE_PATTERNS:
            m = pattern.search(text)
            if m:
                try:
                    sample_date = dateutil_parser.parse(m.group(1), fuzzy=True).date()
                    break
                except Exception:
                    pass

    return {"sample_date": sample_date}


def extract_biomarkers(text: str) -> List[ParsedResult]:
    results: List[ParsedResult] = []
    seen_names: set = set()

    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) < 5:
            continue
        line = _normalize_table_line(line)
        if SKIP_PATTERNS.match(line):
            continue

        m = BIOMARKER_LINE.match(line) or BIOMARKER_INLINE_UNIT.match(line)
        paren_range_match = False
        if not m:
            m = BIOMARKER_WITH_RANGE_FLAG.match(line)
        if not m:
            m = BIOMARKER_WITH_PAREN_RANGE.match(line)
            paren_range_match = m is not None
        if not m:
            m = SINGLE_SPACE_WITH_RANGE.match(line)
        if not m:
            continue

        raw_name = (m.groupdict().get("name") or m.group(1)).strip().rstrip(".,")
        raw_name = _TRAILING_PCT.sub("", raw_name).strip()
        # Meddbase OCR often appends a digit artifact (! misread as 1) to the name
        if paren_range_match:
            raw_name = re.sub(r"\s+\d+\.?\d*$", "", raw_name).strip()
        raw_value = (m.groupdict().get("value") or m.group(2)).strip()
        raw_unit = _normalize_ocr_unit((m.groupdict().get("unit") or m.group(3)).strip())

        if not raw_name or not raw_value or not raw_unit:
            continue
        if _RESULT_FLAGS.match(raw_unit):
            continue  # unit is a result flag (H/L), not a real unit — bad parse

        value = _parse_value(raw_value)
        if value is None:
            continue

        key = raw_name.lower()
        if key in seen_names:
            continue
        seen_names.add(key)

        results.append(ParsedResult(raw_name=raw_name, value=value, unit=raw_unit))

    return results
