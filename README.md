# CrisisMap

CrisisMap is a demo-first humanitarian infrastructure damage assessment dashboard. The current implementation follows the Stitch UI/UX design in `design-system/` and the original product architecture in `CrisisMap_Project_Documentation.docx`.

## What Is Implemented

- FastAPI backend with versioned `/api/v1` endpoints.
- Cached Beirut demo assessment fixture.
- Deterministic damage tiering and priority fallback reasoning.
- TokenRouter-compatible server-side reasoning adapter with safe fallback.
- Next.js App Router frontend with the Stitch operational UI direction.
- Leaflet satellite map with GeoJSON damage polygons and severity legend.
- Workspace, Dashboard, Priority Detail, Report, History, Settings, and Empty State foundations.
- Docker Compose for API, frontend, Redis, worker, and PostGIS.

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Environment

Copy `.env.example` to `.env`. Keep `TOKENROUTER_API_KEY` server-side only. If a key has ever been pasted into chat, rotate it before real use.

## API

- `POST /api/v1/assessments`
- `GET /api/v1/assessments`
- `GET /api/v1/assessments/{id}`
- `GET /api/v1/assessments/{id}/buildings.geojson`
- `GET /api/v1/assessments/{id}/priorities`
- `GET /api/v1/assessments/{id}/report`
- `PATCH /api/v1/settings/analysis`

## Next Steps

- Replace the JSON file store with PostgreSQL/PostGIS models.
- Add real Sentinel/OSM/HDX adapters behind the demo fixture interface.
- Replace placeholder PDF/DOCX export endpoints with generated artifacts.
- Add authentication and team permissions before production deployment.
