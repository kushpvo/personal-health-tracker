# Personal Health Tracker

A self-hosted app for tracking blood work and lab results over time. Upload PDF or image lab reports, review the OCR-extracted values, and visualize trends across tests. Supports multiple users with JWT authentication and an admin panel.

## Features

- **OCR extraction** — upload a PDF or image of any lab report; Tesseract reads the values automatically
- **Review & correct** — edit misread values, relink biomarkers, add or remove rows before saving
- **Trend charts** — plot any biomarker over time with optimal/sufficient/out-of-range zone bands
- **71 built-in biomarkers** across CBC, Lipids, Metabolic, Hormones, Thyroid, Vitamins, Liver, Iron Studies, Inflammation, Minerals, Coagulation, and Cancer Markers panels
- **Unit switching** — change a biomarker's display unit (e.g. mg/dL ↔ mmol/L) and all historical values convert retroactively
- **Multi-user** — each user sees only their own data; admin can manage users and impersonate accounts

## Running with Docker (recommended)

```bash
docker-compose up
```

App is available at `http://localhost:8080`. Lab report files and the database are stored in a persistent Docker volume (`health-tracker-data`).

> **First run:** visit `http://localhost:8080/setup` to create the admin account. Set `SECRET_KEY` to a strong random value in `docker-compose.yml` (or as an environment variable) before deploying — it signs all JWTs.

Generate a secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## Running locally

**Backend** (requires Python 3.12, Tesseract, and poppler):

```bash
# Install system dependencies (macOS)
brew install tesseract poppler

cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

**Frontend** (separate terminal):

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

The Vite dev server proxies `/api` requests to the backend on port 8080.

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy, SQLite |
| Auth | JWT (python-jose), bcrypt (passlib) |
| OCR | Tesseract 4 via pytesseract, pdf2image, OpenCV |
| Frontend | React 19, TypeScript, Vite, TanStack Query |
| Styling | Tailwind CSS |
| Charts | Recharts |

## Adding biomarkers

Biomarkers are defined in `backend/app/db/seed/biomarkers.json`. Each entry includes aliases used for matching OCR output, reference ranges for zone classification, and unit conversion factors. The seed is loaded and synced on every backend startup — add a new entry to the JSON and restart the backend.
