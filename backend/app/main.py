import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api import reports as reports_router
from app.api import biomarkers as biomarkers_router
from app.db.database import Base, SessionLocal, engine
from app.db.seed_loader import load_biomarkers


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables and seed on startup
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE report_results ADD COLUMN sort_order INTEGER"))
        except Exception:
            pass
        try:
            conn.execute(
                text(
                    "ALTER TABLE report_results ADD COLUMN human_matched BOOLEAN DEFAULT 0"
                )
            )
        except Exception:
            pass
    db = SessionLocal()
    try:
        load_biomarkers(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Blood Work Tracker", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports_router.router)
app.include_router(biomarkers_router.router)

# Serve React static build — must come last
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
