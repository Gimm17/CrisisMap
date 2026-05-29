<div align="center">
  <h1>🌍 CrisisMap</h1>
  <p><strong>AI-Powered Humanitarian Infrastructure Damage Assessment Dashboard</strong></p>
  
  [![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
  [![Next.js](https://img.shields.io/badge/Next.js-black?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
  [![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)
</div>

---

**CrisisMap** is a demo-first humanitarian infrastructure damage assessment dashboard designed for post-disaster and conflict-zone analysis. The current implementation follows the *Stitch UI/UX* design guidelines and provides both local AI inference and fallback heuristics to maintain operations in critical scenarios.

## ✨ Features

- **Map-First Workspace:** Interactive Leaflet satellite map with GeoJSON damage polygons, severity legend, and AOI (Area of Interest) drawing tools.
- **AI-Powered Inference:** Damage assessment using Siamese CNN (`SiamUnet`) with a deterministic image-change fallback.
- **Automated Reasoning:** TokenRouter-compatible server-side reasoning adapter that generates readable impact reports.
- **Export Ready:** Generate and download actionable PDF, DOCX, and GeoJSON reconstruction reports.
- **Complete Dashboard:** Includes Workspace, Dashboard, Priority Detail, Report, History, Settings, and Empty State foundations.

## 📸 Visual Overview

<div align="center">
  <img src="SCREENSHOTS/Screenshot%202026-05-30%20021725.png" alt="Results Dashboard" width="800"/>
  <br/>
  <i>Dashboard mapping showing localized severe/critical building damage and affected zones.</i>
  <br/><br/>

  <img src="SCREENSHOTS/Screenshot%202026-05-30%20022559.png" alt="Interactive Split View Workspace" width="800"/>
  <br/>
  <i>Interactive split-view map workspace for analyzing before and after infrastructure state.</i>
  <br/><br/>

  <img src="SCREENSHOTS/Screenshot%202026-05-30%20022721.png" alt="Generated Automated Reports" width="800"/>
  <br/>
  <i>Exportable post-incident AI assessment reports containing prioritized reconstruction plans.</i>
</div>

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI (`/api/v1`), SQLAlchemy
- **Frontend:** Next.js (App Router), React, TailwindCSS, Leaflet
- **Infrastructure:** Docker Compose (API, Frontend, Redis, Celery Worker, PostGIS)
- **Machine Learning:** PyTorch (Local inference)

## 🚀 Quick Start

### 1. Environment Setup

Copy the example environment file:
```bash
cp .env.example .env
```
> [!IMPORTANT]
> Keep `TOKENROUTER_API_KEY` server-side only. If a key has ever been pasted into chat, rotate it before real use.

### 2. Run Backend (FastAPI)

```bash
cd backend
python -m venv .venv

# Activate the virtual environment
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```
*API will run at `http://localhost:8000`*

### 3. Run Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```
*Frontend will run at `http://localhost:3000`*

### 4. (Optional) Run with Docker

```bash
docker compose up --build
```

## 📡 Core API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/assessments` | Create a new damage assessment |
| `GET` | `/api/v1/assessments` | List history of assessments |
| `GET` | `/api/v1/assessments/{id}` | Get specific assessment details |
| `GET` | `/api/v1/assessments/{id}/buildings.geojson` | Retrieve map damage polygons |
| `GET` | `/api/v1/assessments/{id}/priorities` | Get infrastructure priority list |
| `GET` | `/api/v1/assessments/{id}/report` | Retrieve reasoning report |
| `PATCH`| `/api/v1/settings/analysis` | Update system analysis settings |

## 🎯 Next Steps (Roadmap)

- [ ] Replace the JSON file store with PostgreSQL/PostGIS models completely.
- [ ] Add real Sentinel/OSM/HDX adapters behind the demo fixture interface.
- [ ] Replace placeholder PDF/DOCX export endpoints with generated artifacts.
- [ ] Add authentication and team permissions before production deployment.

---
<div align="center">
  <i>Built for humanitarian responders, NGOs, and disaster analysis teams.</i>
</div>
