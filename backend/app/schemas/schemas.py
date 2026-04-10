from __future__ import annotations
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel


# ── Reports ───────────────────────────────────────────────────────────────────

class ReportUploadResponse(BaseModel):
    id: int
    status: str


class ReportStatus(BaseModel):
    id: int
    status: str
    error_message: Optional[str] = None


class ReportListItem(BaseModel):
    id: int
    report_name: Optional[str]
    original_filename: str
    sample_date: Optional[date]
    uploaded_at: datetime
    status: str
    result_count: int

    class Config:
        from_attributes = True


# ── Biomarker detail (for trend chart) ────────────────────────────────────────

class BiomarkerInfo(BaseModel):
    id: int
    name: str
    category: Optional[str]
    default_unit: Optional[str]
    optimal_min: Optional[float]
    optimal_max: Optional[float]
    sufficient_min: Optional[float]
    sufficient_max: Optional[float]
    alternate_units: List[str] = []

    class Config:
        from_attributes = True


class ResultPoint(BaseModel):
    """One data point on the trend chart."""
    id: int
    report_id: int
    report_name: Optional[str]
    sample_date: Optional[date]
    value: float
    unit: str
    zone: str  # "optimal" | "sufficient" | "out_of_range" | "unknown"

    class Config:
        from_attributes = True


class BiomarkerDetail(BaseModel):
    biomarker: BiomarkerInfo
    results: List[ResultPoint]


# ── Dashboard summary ──────────────────────────────────────────────────────────

class BiomarkerSummary(BaseModel):
    biomarker: BiomarkerInfo
    latest_value: float
    latest_unit: str
    latest_date: Optional[date]
    latest_zone: str
    result_count: int


# ── Review flow ────────────────────────────────────────────────────────────────

class ReportResultItem(BaseModel):
    id: int
    raw_name: str
    value: float
    unit: str
    is_flagged_unknown: bool
    human_matched: bool
    sort_order: Optional[int]
    biomarker_id: Optional[int]
    biomarker_name: Optional[str]

    class Config:
        from_attributes = True


class ReviewResultInput(BaseModel):
    id: int
    value: float
    unit: str
    biomarker_id: Optional[int] = None


class ReviewReportInput(BaseModel):
    report_name: str
    sample_date: Optional[date] = None
    results: List[ReviewResultInput]


class BiomarkerListItem(BaseModel):
    id: int
    name: str
    category: Optional[str]
    default_unit: Optional[str]
    alternate_units: List[str] = []

    class Config:
        from_attributes = True


class ChangeDefaultUnitInput(BaseModel):
    unit: str
