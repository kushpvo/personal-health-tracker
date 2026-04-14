from datetime import datetime
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float,
    ForeignKey, Integer, JSON, String, Text,
)
from sqlalchemy.orm import relationship
from app.db.database import Base


class Biomarker(Base):
    __tablename__ = "biomarkers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    loinc_code = Column(String)
    aliases = Column(JSON, default=list)       # list[str], lowercase normalized
    category = Column(String)
    description = Column(Text)
    default_unit = Column(String)
    alternate_units = Column(JSON, default=list)  # list[str]
    optimal_min = Column(Float)
    optimal_max = Column(Float)
    sufficient_min = Column(Float)
    sufficient_max = Column(Float)
    # {"from_unit": {"to_unit": factor}}
    # e.g. {"mg/dL": {"mmol/L": 0.02586}}
    unit_conversions = Column(JSON, default=dict)

    results = relationship("ReportResult", back_populates="biomarker")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    reports = relationship("Report", back_populates="owner")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    report_name = Column(String)
    sample_date = Column(Date)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    ocr_raw_text = Column(Text)
    status = Column(String, default="pending")   # pending|processing|done|failed
    error_message = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="reports")
    results = relationship(
        "ReportResult", back_populates="report", cascade="all, delete-orphan"
    )


class ReportResult(Base):
    __tablename__ = "report_results"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    biomarker_id = Column(Integer, ForeignKey("biomarkers.id"), nullable=True)
    raw_name = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    is_flagged_unknown = Column(Boolean, default=False)
    sort_order = Column(Integer, nullable=True)
    human_matched = Column(Boolean, default=False)
    notes = Column(Text)

    report = relationship("Report", back_populates="results")
    biomarker = relationship("Biomarker", back_populates="results")


class UnknownBiomarker(Base):
    __tablename__ = "unknown_biomarkers"

    id = Column(Integer, primary_key=True, index=True)
    raw_name = Column(String, nullable=False, unique=True)
    raw_unit = Column(String)
    times_seen = Column(Integer, default=1)
    first_seen_at = Column(DateTime, nullable=False)
    last_seen_at = Column(DateTime, nullable=False)
    resolved_biomarker_id = Column(Integer, ForeignKey("biomarkers.id"), nullable=True)
