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

This is a multi-user, self-hosted blood work / lab report tracker. Users log in with JWT + refresh tokens, upload PDF or image lab reports, and an OCR pipeline extracts biomarker values which are stored, reviewed, and visualized over time. An admin panel supports user management and impersonation.

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
  → User reviews on /reports/{id}/review (edit values, link biomarkers, add/delete rows, add tags/notes)
  → Dashboard shows latest values + trend alerts; BiomarkerDetail shows historical trends
```

### Backend (`backend/app/`)

| Path | Purpose |
|------|---------|
| `main.py` | FastAPI setup, CORS (ALLOWED_ORIGINS), lifespan (DB init + seed + migrations), routing |
| `api/auth.py` | Auth endpoints: setup, login, /me, change-password, refresh, logout |
| `api/admin.py` | Admin endpoints: user CRUD, impersonation |
| `api/reports.py` | Upload, list (with date filter), status, results, review, delete, reprocess |
| `api/biomarkers.py` | Summary (with search/category filter), detail (trend), list, unit override |
| `api/export.py` | PDF export of latest biomarker results |
| `api/unknowns.py` | List and resolve unknown biomarkers |
| `core/auth.py` | JWT creation/validation (15-min access tokens), password hashing, auth dependencies |
| `db/models.py` | SQLAlchemy ORM: `User`, `Biomarker`, `Report`, `ReportResult`, `UnknownBiomarker`, `RefreshToken` |
| `db/database.py` | SQLite session factory; DB file at `./data/db.sqlite` |
| `db/seed_loader.py` | Loads/syncs `biomarkers.json` into the DB on startup |
| `db/seed/biomarkers.json` | Reference data: names, aliases, categories, units, ranges, conversions |
| `services/pipeline.py` | Orchestrates the full OCR → parse → match → store workflow |
| `services/parser.py` | Regex-based text → biomarker tuples (handles multiple lab formats) |
| `services/preprocessor.py` | pdf2image + OpenCV preprocessing before OCR |
| `services/unit_converter.py` | Unit conversion using per-biomarker factor tables from seed |
| `schemas/schemas.py` | Pydantic request/response models |

**Auth:** JWT access tokens (15 min) + httpOnly refresh token cookies (30 days). First startup hits `/setup` to create the admin account. Refresh tokens stored in DB with `RefreshToken` model. Admin users can create additional users and impersonate them (8-hour scoped token). All data endpoints filtered by effective user ID (supports impersonation via `acting_as` claim).

**Schema migrations:** Raw SQL in `main.py` lifespan (ALTER TABLE ... ADD COLUMN). Wrapped in try/except for safe re-runs.

**Environment variables:** `SECRET_KEY` (required), `DATA_DIR` (default `./data`), `ALLOWED_ORIGINS`, `MAX_UPLOAD_MB`, `OCR_BACKEND`.

### Frontend (`frontend/src/`)

| Path | Purpose |
|------|---------|
| `App.tsx` | React Router v6 — public routes (login/setup) + protected routes |
| `components/ProtectedRoute.tsx` | Redirects to `/login` if no token |
| `components/AdminRoute.tsx` | Redirects non-admins to `/` |
| `pages/Login.tsx` | Login form; redirects to `/setup` if no users exist |
| `pages/Setup.tsx` | First-run admin account creation |
| `pages/Dashboard.tsx` | Latest biomarker values with search/filter, group by category/zone, trend alerts, PDF export |
| `pages/Reports.tsx` | All reports list with date range filter, tags display, reprocess button |
| `pages/Upload.tsx` | File upload form + status polling |
| `pages/ReportDashboard.tsx` | Single report's biomarkers (click from Reports) |
| `pages/ReviewReport.tsx` | Edit OCR results: values, units, biomarker links, tags, notes, add/delete rows |
| `pages/BiomarkerDetail.tsx` | Trend chart (Recharts) for a single biomarker over time |
| `pages/UnknownBiomarkers.tsx` | Link unrecognized OCR names to known biomarkers |
| `pages/Settings.tsx` | Change password |
| `pages/Admin.tsx` | User table, create user, deactivate, reset password, impersonate |
| `components/Layout.tsx` | Sidebar nav with role-aware links, dark mode toggle, impersonation banner, logout |
| `components/TrendChart.tsx` | Line chart with zone bands (optimal/sufficient/out-of-range) |
| `components/BiomarkerCard.tsx` | Card showing latest value with trend alert indicator |
| `lib/api.ts` | Typed fetch client — handles token refresh on 401, injects Bearer token |
| `lib/auth.ts` | Token storage (localStorage), impersonation helpers, logout |
| `lib/utils.ts` | Zone color/label helpers |

**State management:** TanStack React Query for all server state. No global client state store.

**API proxy:** Vite dev server proxies `/api/*` → `http://localhost:8080`. In production, built frontend served as static files from FastAPI at `/`.

### Zone System

Biomarkers have `optimal_min/max` and `sufficient_min/max` float bounds (from seed data). A value's zone is `optimal`, `sufficient`, or `out_of_range`. Tailwind custom colors map to these: `optimal` (#22c55e), `sufficient` (#06b6d4), `out_of_range` (#f97316).

### Trend Alerts

The dashboard shows a trend alert indicator (orange dot) when:
- Latest value changed by ≥20% from the previous result, OR
- Zone crossed between last two results (e.g., optimal → out_of_range)

The `BiomarkerSummary` API response includes `trend_delta` (percentage change) and `trend_alert` (boolean).

### Search & Filter

- **Reports:** Filter by `from_date` and `to_date` query params (filters by `sample_date`)
- **Dashboard:** Filter biomarkers by `search` (name contains) and `category` query params

### Report Tags & Notes

- **Tags:** Free-text comma-separated tags stored on `Report` (e.g., "Annual Physical, Fasting")
- **Notes:** Per-result notes stored on `ReportResult`, editable inline on Review page

### Biomarker Matching

The parser produces a `raw_name` string from OCR text. The matcher compares this (lowercased, normalized) against each `Biomarker.aliases` list (JSON array in DB, also from seed). Unknown biomarkers are tracked in the `UnknownBiomarker` table and can be resolved via the `/unknown-biomarkers` page — resolving appends the raw_name to the biomarker's aliases for future automatic matching.
