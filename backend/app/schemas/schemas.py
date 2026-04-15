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
    tags: Optional[str] = None

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
    trend_delta: Optional[float] = None   # % change from previous result
    trend_alert: bool = False             # True if delta ≥ 20% or zone changed


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
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class ReviewResultInput(BaseModel):
    id: int
    value: float
    unit: str
    biomarker_id: Optional[int] = None


class NewResultInput(BaseModel):
    biomarker_id: int
    value: float
    unit: str


class ReviewReportInput(BaseModel):
    report_name: str
    sample_date: Optional[date] = None
    results: List[ReviewResultInput]
    new_results: List[NewResultInput] = []
    deleted_result_ids: List[int] = []
    tags: Optional[str] = None
    result_notes: dict[int, str] = {}


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


# ── Unknowns ──────────────────────────────────────────────────────────────────

class UnknownBiomarkerItem(BaseModel):
    id: int
    raw_name: str
    raw_unit: Optional[str]
    times_seen: int
    first_seen_at: datetime
    last_seen_at: datetime
    resolved_biomarker_id: Optional[int]

    class Config:
        from_attributes = True


class ResolveUnknownInput(BaseModel):
    biomarker_id: int


# ── Supplements ───────────────────────────────────────────────────────────────

class SupplementDoseItem(BaseModel):
    id: int
    dose: float
    started_on: date
    ended_on: Optional[date] = None
    is_active: bool

    class Config:
        from_attributes = True


class SupplementLogItem(BaseModel):
    id: int
    name: str
    unit: str
    frequency: str
    notes: Optional[str] = None
    created_at: datetime
    doses: List[SupplementDoseItem] = []

    class Config:
        from_attributes = True


class CreateSupplementInput(BaseModel):
    name: str
    unit: str
    frequency: str
    dose: float
    started_on: date
    notes: Optional[str] = None


class UpdateSupplementInput(BaseModel):
    name: Optional[str] = None
    unit: Optional[str] = None
    frequency: Optional[str] = None
    notes: Optional[str] = None


class AddDoseInput(BaseModel):
    dose: float
    started_on: date


class UpdateDoseInput(BaseModel):
    dose: Optional[float] = None
    started_on: Optional[date] = None
    ended_on: Optional[date] = None


# ── Auth ──────────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginInput(BaseModel):
    username: str
    password: str


class SetupInput(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class ChangePasswordInput(BaseModel):
    current_password: str
    new_password: str


# ── Admin ─────────────────────────────────────────────────────────────────────

class CreateUserInput(BaseModel):
    username: str
    password: str
    role: str = "user"


class UpdateUserInput(BaseModel):
    is_active: Optional[bool] = None
    password: Optional[str] = None
