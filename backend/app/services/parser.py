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
    return unit


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
        if SKIP_PATTERNS.match(line):
            continue

        m = BIOMARKER_LINE.match(line) or BIOMARKER_INLINE_UNIT.match(line)
        if not m:
            m = BIOMARKER_WITH_RANGE_FLAG.match(line)
        if not m:
            m = SINGLE_SPACE_WITH_RANGE.match(line)
        if not m:
            continue

        raw_name = (m.groupdict().get("name") or m.group(1)).strip().rstrip(".,")
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
