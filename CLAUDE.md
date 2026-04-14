# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend (Python/FastAPI)
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

Run tests:
```bash
cd backend
pytest                          # all tests
pytest tests/test_parser.py     # single file
pytest tests/test_parser.py -k "test_name"  # single test
```

### Frontend (React/TypeScript)
```bash
cd frontend
npm run dev      # Vite dev server at http://localhost:5173 (proxies /api → :8080)
npm run build    # tsc + Vite build → outputs to ../backend/static
npm run lint     # ESLint
```

### Docker (production)
```bash
docker-compose up   # Serves everything at http://localhost:8080
```

## Architecture

This is a multi-user, self-hosted blood work / lab report tracker. Users log in with a JWT, upload PDF or image lab reports, and an OCR pipeline extracts biomarker values which are stored, reviewed, and visualized over time. An admin panel supports user management and impersonation.

### Data Flow

```
Upload (PDF/image)
  → FastAPI saves file, creates Report row (status: pending)
  → Background task: pipeline.py
      → preprocessor.py: PDF/image → temp PNG files
      → ocr/tesseract.py: images → raw text
      → parser.py: regex extracts (raw_name, value, unit, range, flag) tuples
      → matcher: raw_name fuzzy-matched against Biomarker.aliases
      → unit_converter.py: value converted to Biomarker.default_unit
      → ReportResult rows stored in SQLite
  → Report status: done (or failed)
  → Frontend polls /api/reports/{id}/status
  → User reviews on /reports/{id}/review (edit values, link biomarkers, add/delete rows)
  → Dashboard + BiomarkerDetail show historical trends
```

### Backend (`backend/app/`)

| Path | Purpose |
|------|---------|
| `main.py` | FastAPI setup, CORS, lifespan (DB init + seed), routing |
| `api/auth.py` | Auth endpoints: setup, login, /me, change-password |
| `api/admin.py` | Admin endpoints: user CRUD, impersonation |
| `api/reports.py` | Upload, list, status, results, review, delete endpoints (per-user isolated) |
| `api/biomarkers.py` | Summary (dashboard), detail (trend), unit override endpoints (per-user isolated) |
| `core/auth.py` | JWT creation/validation, password hashing, FastAPI auth dependencies |
| `db/models.py` | SQLAlchemy ORM: `User`, `Biomarker`, `Report`, `ReportResult`, `UnknownBiomarker` |
| `db/database.py` | SQLite session factory; DB file at `./data/db.sqlite` |
| `db/seed_loader.py` | Loads/syncs `biomarkers.json` into the DB on startup |
| `db/seed/biomarkers.json` | Reference data: names, aliases, categories, units, ranges, conversions |
| `services/pipeline.py` | Orchestrates the full OCR → parse → match → store workflow |
| `services/parser.py` | Regex-based text → biomarker tuples (handles multiple lab formats) |
| `services/preprocessor.py` | pdf2image + OpenCV preprocessing before OCR |
| `services/unit_converter.py` | Unit conversion using per-biomarker factor tables from seed |
| `schemas/schemas.py` | Pydantic request/response models |

**Auth:** JWT (python-jose, HS256) with 30-day tokens stored in `localStorage`. First startup hits `/setup` to create the admin account. Admin users can create additional users and impersonate them (8-hour scoped token). All data endpoints are filtered by the effective user ID (supports impersonation via `acting_as` claim).

**Schema migrations** are run as raw SQL in `main.py` lifespan (ALTER TABLE ... ADD COLUMN). They're wrapped in try/except so re-runs are safe.

**Environment variables:** `DATA_DIR` (default `./data`), `OCR_BACKEND` (only `tesseract`), `MAX_UPLOAD_MB` (default 50), `SECRET_KEY` (required in production — signs JWTs).

### Frontend (`frontend/src/`)

| Path | Purpose |
|------|---------|
| `App.tsx` | React Router setup — public routes (login/setup) + protected routes |
| `components/ProtectedRoute.tsx` | Redirects to `/login` if no token |
| `components/AdminRoute.tsx` | Redirects non-admins to `/` |
| `pages/Login.tsx` | Login form; redirects to `/setup` if no users exist |
| `pages/Setup.tsx` | First-run admin account creation |
| `pages/Dashboard.tsx` | Latest biomarker values; group by category or zone |
| `pages/Reports.tsx` | All uploaded reports list |
| `pages/Upload.tsx` | File upload form + status polling |
| `pages/ReportDashboard.tsx` | Single report's biomarkers (click from Reports) |
| `pages/ReviewReport.tsx` | Edit OCR results: values, units, biomarker links, add/delete rows |
| `pages/BiomarkerDetail.tsx` | Trend chart (Recharts) for a single biomarker over time |
| `pages/Settings.tsx` | Change password |
| `pages/Admin.tsx` | User table, create user, deactivate, reset password, impersonate |
| `components/Layout.tsx` | Sidebar nav with role-aware links, impersonation banner, logout button |
| `components/TrendChart.tsx` | Line chart with zone bands (optimal/sufficient/out-of-range) |
| `lib/api.ts` | Typed fetch client — all API calls go through here; injects Bearer token; redirects on 401 |
| `lib/auth.ts` | Token storage (localStorage), impersonation helpers, JWT payload parsing |
| `lib/utils.ts` | Zone color/label helpers |

**State management:** TanStack React Query for all server state. No global client state store.

**API proxy:** Vite dev server proxies `/api/*` → `http://localhost:8080`. In production, the built frontend is served as static files from FastAPI at `/`.

### Zone System

Biomarkers have `optimal_min/max` and `sufficient_min/max` float bounds (from seed data). A value's zone is `optimal`, `sufficient`, or `out_of_range`. Tailwind custom colors map to these: `optimal` (#22c55e), `sufficient` (#06b6d4), `out_of_range` (#f97316).

### Biomarker Matching

The parser produces a `raw_name` string from OCR text. The matcher compares this (lowercased, normalized) against each `Biomarker.aliases` list (JSON array in DB, also from seed). When adding new biomarkers or fixing mismatches, update `biomarkers.json` and keep aliases in sync — `seed_loader.py` merges on startup but won't drop aliases already in the DB.
