import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api import admin as admin_router
from app.api import auth as auth_router
from app.api import reports as reports_router
from app.api import biomarkers as biomarkers_router
from app.api import export as export_router
from app.api import unknowns as unknowns_router
from app.api import supplements as supplements_router
from app.db.database import Base, SessionLocal, engine
from app.db.seed_loader import load_biomarkers


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run column migrations before create_all so ALTER TABLE applies to existing DBs.
    # On a fresh DB these will fail (table doesn't exist yet) and be swallowed — create_all
    # then creates the table with the columns already in the model definition.
    with engine.begin() as conn:
        for stmt in [
            "ALTER TABLE report_results ADD COLUMN sort_order INTEGER",
            "ALTER TABLE report_results ADD COLUMN human_matched BOOLEAN DEFAULT 0",
            "ALTER TABLE reports ADD COLUMN tags TEXT",
            "ALTER TABLE report_results ADD COLUMN notes TEXT",
            "ALTER TABLE users ADD COLUMN sex TEXT",
            "ALTER TABLE biomarkers ADD COLUMN sex TEXT",
        ]:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass  # column already exists, or table not yet created (fresh DB)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        load_biomarkers(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Blood Work Tracker", lifespan=lifespan)

_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports_router.router)
app.include_router(biomarkers_router.router)
app.include_router(auth_router.router)
app.include_router(admin_router.router)
app.include_router(export_router.router)
app.include_router(unknowns_router.router)
app.include_router(supplements_router.router)

# Serve React static build — must come last
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
