# Personal Health Tracker

<p align="center">
  <img src="frontend/src/assets/hero.png" alt="Personal Health Tracker" width="120">
</p>

<p align="center">
  A self-hosted web app for tracking blood work and lab results over time.
</p>

Upload PDF or image lab reports and let the app automatically extract your biomarker values. Review, correct, and visualize trends across tests — all in one place. Supports multiple users with admin management, so your whole household or clinic can use a single instance.

---

## Features

- **Automatic OCR extraction** — Upload a PDF or photo of any lab report; the app reads values automatically using Tesseract OCR
- **Review & correct** — Edit misread values, relink biomarkers, add or delete rows before saving to your history
- **71 built-in biomarkers** across CBC, Lipids, Metabolic, Hormones, Thyroid, Vitamins, Liver, Iron Studies, Inflammation, Minerals, Coagulation, and Cancer Markers
- **Sex-aware reference ranges** — Set your biological sex in profile settings for more accurate optimal/sufficient range matching
- **Trend charts** — Plot any biomarker over time with color-coded zone bands (optimal, sufficient, out-of-range)
- **Supplement & medication log** — Track doses and visualize them as overlays on your biomarker trend charts
- **Trend alerts** — Dashboard flags biomarkers with ≥20% change or zone crossings between the last two results
- **Unit switching** — Change display units (e.g. mg/dL ↔ mmol/L) and all historical values convert retroactively
- **Custom PDF export** — Generate a personalized PDF summary with selected biomarkers, charts, and supplement lists
- **Multi-user with admin panel** — Each user sees only their own data; admins can create accounts, reset passwords, and impersonate users
- **Search & filter** — Filter reports by date range; search and filter biomarkers by name or category
- **Report tags & notes** — Tag reports (e.g. "Annual Physical, Fasting") and add private notes to individual results
- **Unknown biomarker resolution** — Link unrecognized lab names to known biomarkers so future uploads match automatically
- **Dark mode** — Toggle between light and dark themes; preference is remembered
- **ARM64 support** — Prebuilt images available for both AMD64 and ARM64 (Apple Silicon, Raspberry Pi, etc.)

---

## Quick Start (Docker)

The easiest way to run the app is with Docker Compose. Everything — the web UI, API, database, and file storage — runs in a single container with a persistent volume.

### 1. Generate a secret key

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output. This key is used to sign authentication tokens.

### 2. Create a `docker-compose.yml`

```yaml
services:
  app:
    image: ghcr.io/kushpvo/personal-health-tracker:latest
    container_name: health-tracker
    ports:
      - "8080:8080"
    volumes:
      - health-tracker-data:/app/data
    environment:
      - SECRET_KEY=replace-with-your-generated-key
      - DATA_DIR=/app/data
      - OCR_BACKEND=tesseract
      - MAX_UPLOAD_MB=50
    restart: unless-stopped

volumes:
  health-tracker-data:
```

> **Security:** Replace `SECRET_KEY` with the value you generated above. Do not use the default in production.

### 3. Start the app

```bash
docker compose up -d
```

The app will be available at **`http://localhost:8080`**.

### 4. Create the admin account

On first run, visit **`http://localhost:8080/setup`** to create your admin user. This account can then create additional users from the Admin panel.

---

## Updating

To update to the latest version:

```bash
docker compose pull
docker compose up -d
```

Your data is preserved in the Docker volume `health-tracker-data`.

---

## Running without Docker

If you prefer to run directly on your machine:

**Requirements:** Python 3.12, Node.js 20, Tesseract OCR, and poppler

```bash
# macOS example
brew install tesseract poppler

# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080

# Frontend (in a new terminal)
cd frontend
npm install
npm run dev   # http://localhost:5173
```

The Vite dev server proxies API requests to the backend automatically.

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | *(required)* | Cryptographic key for signing login tokens. Generate once and keep secret. |
| `DATA_DIR` | `./data` | Where SQLite and uploaded files are stored. |
| `MAX_UPLOAD_MB` | `50` | Maximum lab report file size. |
| `ALLOWED_ORIGINS` | *(auto)* | Only needed if accessing the API from a different domain than the app. |

---

## Screenshots

*Screenshots of the dashboard, review page, and trend charts will be added here.*

> The app features a clean, responsive web interface with a collapsible sidebar, searchable biomarker cards, interactive Recharts trend graphs with zone bands, and a full review workflow for every uploaded report.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy, SQLite |
| Frontend | React 19, TypeScript, Vite, TanStack Query |
| Styling | Tailwind CSS |
| Charts | Recharts |
| OCR | Tesseract 4, pdf2image, OpenCV |
| PDF Export | reportlab |

---

## License

MIT
