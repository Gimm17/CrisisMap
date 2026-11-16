# CrisisMap Feature Audit Report

Based on a thorough review of the codebase (both frontend and backend) and the live system at `http://localhost:3000/`, here is the breakdown of the current state of CrisisMap features.

## 🟢 Fully Functional / Dynamic Features
These features are fully implemented and function as intended without relying on static mock data (assuming the backend is running).

- **Map Rendering & Overlays:** The Leaflet map (`DynamicDamageMap`) dynamically renders GeoJSON polygons and color-codes them based on severity metrics. 
- **Layer Toggles:** The ability to toggle specific infrastructure overlays (e.g., Medical Facilities, Power Grids) is fully implemented using React state in `dashboard/page.tsx`.
- **Backend API Routing:** The FastAPI backend is fully configured with proper routes (`/api/v1/assessments`) to handle JSON requests, serve GeoJSON, and provide priority lists.
- **Report Generation Engine:** The backend actively builds exportable files (`build_docx_export`, `build_pdf_export`) dynamically based on the assessment payload it receives.

## 🧠 AI Engine & Backend Processing
These features utilize the backend and the underlying ML pipeline.

- **AI Inference Pipeline:** The backend contains a robust pipeline (`run_assessment`) designed to use the Siamese CNN (`SiamUnet`).
- **TokenRouter / Automated Reasoning:** The backend is set up to synthesize data using an AI reasoning adapter. However, the default demo mode uses a `heuristic-fallback` provider (local deterministic scoring) rather than burning real API credits unless explicitly configured.
- **Backend Resilience:** The backend uses `store.get()` to retrieve in-memory/JSON jobs. If an ID is missing, it falls back to `ensure_demo_assessment()` to ensure the frontend never crashes.

## ⚠️ Hardcoded / Static Features (The "Demo" Layer)
CrisisMap is currently designed as a **Demo-First** application. To ensure the UI always works perfectly for demonstrations, there is a substantial layer of hardcoded fallback data.

- **Frontend Silent Fallbacks (`lib/api.ts`):** 
  Every API call is wrapped in a `getEnvelope` function. If the FastAPI backend is offline, or if an endpoint throws an error, the frontend silently catches the error and returns **hardcoded static data** from `lib/demo.ts`.
- **Static Demo Data (`lib/demo.ts`):**
  - `demoAssessment`: Hardcoded stats (1,420 buildings assessed, 84 severe).
  - `demoPriorities`: Hardcoded list of 3 critical infrastructure assets (St. George Hospital, Port Silo, Power Substation).
  - `demoReport`: A hardcoded narrative donor summary and phased reconstruction plan.
  - `demoGeoJson`: Hardcoded polygon coordinates for Beirut.
- **Assessment ID:** The dashboard defaults to `?assessment=demo`. When the backend sees the ID `"demo"`, it intentionally bypasses live inference and serves the pre-computed fixture data (`ensure_demo_assessment()`).

## 🎯 Summary
**The UI/UX is 100% complete and fully reactive.** However, unless a user actively triggers a *new* assessment through the Workspace UI (which hits the `POST /api/v1/assessments` endpoint to spin up the real PyTorch pipeline), the dashboard will safely serve the highly polished, hardcoded Beirut demo data. 

To see the real AI engine work, you must execute a live job rather than relying on the default `/dashboard` route.
