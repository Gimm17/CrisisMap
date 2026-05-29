# CrisisMap Local Running, Testing, And Usage Guide

Dokumen ini menjelaskan cara menjalankan CrisisMap di local machine, cara testing, tutorial penggunaan UI, fungsi setiap fitur, dan status data/pipeline saat ini.

Project path:

```text
C:\Users\HP\Laravel\CrisisMap
```

## 1. Status Implementasi Saat Ini

CrisisMap saat ini sudah memiliki:

- Backend FastAPI dengan endpoint `/api/v1`.
- Frontend Next.js App Router.
- UI operasional sesuai desain Stitch: Workspace, Dashboard, Priority Detail, Reports, History, Settings, Docs.
- Leaflet map dengan GeoJSON damage polygon.
- AOI polygon drawing aktual di Workspace: klik titik di map, validasi area/vertex, clear/finalize, lalu kirim sebagai `aoi_geojson`.
- Beirut V1 public-data pipeline dari Copernicus EMSR452 damage points untuk mode demo.
- Beirut live pipeline dari Maxar pre/post GeoTIFF + Maxar building footprints + `SiamUnet` ML inference jika PyTorch/checkpoint siap.
- Deterministic image-change scoring tetap tersedia sebagai fallback otomatis jika dependency ML, checkpoint, atau model load gagal.
- Source readiness endpoint untuk PostGIS, OSM, HDX, local imagery, xBD, TokenRouter, dan Sentinel placeholder.
- SQLAlchemy/PostGIS persistence dengan fallback JSON store jika database tidak aktif, plus migration Alembic minimal.
- xBD/xView2 external dataset registry, validator, manifest generator, dan baseline pre/post image-change inference sample.
- TokenRouter reasoning server-side dengan fallback heuristic.
- Export PDF, DOCX, dan GeoJSON.
- Data publik Beirut di `data/raw/`, termasuk Maxar pre/post imagery, OSM, EMSR452 ground truth, HDX, WorldPop, dan baseline model.

Catatan penting:

- UI dan API demo/live baseline sudah bisa dijalankan secara lokal.
- Damage result dashboard memakai hasil assessment persisted. Mode demo memakai Copernicus EMSR452 jika tersedia, lalu fallback ke fixture. Mode live memakai local Maxar imagery/footprints dengan `ml-inference` saat model tersedia, atau `imagery-baseline` saat fallback aktif.
- xBD train dan tier3 dipakai untuk validasi dataset, manifest, parsing polygon, dan baseline inference sample. Fine-tuning/deep model xBD belum dijalankan lokal.
- TokenRouter dipakai untuk reasoning/report text, bukan untuk membaca pixel imagery.
- Model CV lokal sudah tersambung untuk inference checkpoint. Training/fine-tuning berat tetap dilakukan terpisah di Kaggle/Colab, lalu checkpoint hasil training bisa menggantikan `model_best.pth.tar`.
- Backend punya quality gate untuk membedakan `ml-inference`, `imagery-baseline`, dan `copernicus-validation`.

## 2. Struktur Project Penting

```text
CrisisMap/
  backend/
    app/
      api/v1/routes/          # Route FastAPI
      services/               # Pipeline, export, reasoning, fixture loader
      services/xbd/           # xBD validator, manifest, preprocessing, baseline inference
      models/schemas.py       # Pydantic schemas
    tests/                    # Backend unit/integration tests
    requirements.txt

  frontend/
    src/app/                  # Next.js pages
    src/components/           # Layout, map, UI components
    src/lib/                  # API client, demo fallback, types
    package.json

  data/
    fixtures/beirut/          # Demo JSON fixture
    raw/                      # Dataset publik yang sudah didownload, ignored by git
    DOWNLOADS.md              # Catatan dataset lokal
    public_data_download_manifest.json

  scripts/
    download_public_beirut_data.ps1
    generate_xbd_manifest.py

  docker-compose.yml
  README.md
```

## 3. Environment

Jangan simpan API key di frontend. TokenRouter key hanya boleh berada di backend/server environment.

Untuk local manual, buat file backend env:

```powershell
cd C:\Users\HP\Laravel\CrisisMap
Copy-Item .env.example backend\.env
```

Edit `backend\.env`:

```env
TOKENROUTER_API_KEY=isi_key_tokenrouter_di_sini
TOKENROUTER_BASE_URL=https://api.tokenrouter.com/v1
TOKENROUTER_MODEL=openai/gpt-5.4
DATA_DIR=../data
DEMO_FIXTURE_DIR=../data/fixtures/beirut
ARTIFACTS_DIR=./artifacts
DATABASE_URL=postgresql+psycopg://crisismap:crisismap@localhost:5432/crisismap
POSTGIS_ENABLED=true
OVERPASS_URL=https://overpass-api.de/api/interpreter
CRISISMAP_DATA_ROOT=E:/CrisisMapData
XBD_TRAIN_ROOT=E:/CrisisMapData/xbd/extracted/train/train
XBD_TIER3_ROOT=E:/CrisisMapData/xbd/extracted/tier3/tier3
BEIRUT_GROUND_TRUTH_PATH=../data/raw/ground_truth/copernicus_ems/EMSR452/extracted/EMSR452_AOI01_GRA_PRODUCT_builtUpP_r1_v2.json
HDX_LOCAL_ROOT=../data/raw/humanitarian/hdx
WORLDPOP_INDEX_PATH=../data/raw/population/worldpop/LBN/2020/worldpop_lbn_wpgp_index.json
BEIRUT_MAXAR_PRE_PATH=../data/raw/imagery/maxar/beirut_explosion/pre_event_2020-07-31_10300500A5F95600.tif
BEIRUT_MAXAR_POST_PATH=../data/raw/imagery/maxar/beirut_explosion/post_event_2020-08-05_104001005EBCEB00.tif
BEIRUT_FOOTPRINTS_PATH=../data/raw/vector/maxar/beirut_explosion/extracted/Beirut-Explosion-2D-building-32636/Beirut-Explosion-2D-building-32636.shp
BEIRUT_OAM_POST_PATH=../data/raw/imagery/openaerialmap/beirut_aoi/post_event_uav_2020-08-05_beirut_port_012m.tif
OSM_OVERPASS_LOCAL_PATH=../data/raw/vector/osm/beirut_aoi/overpass_beirut_infrastructure.json
BEIRUT_MAX_BUILDINGS=300
ML_MODEL_ENABLED=true
ML_MODEL_CHECKPOINT_PATH=../data/raw/models/microsoft_building_damage_assessment_cnn_siamese/model_best.pth.tar
ML_MODEL_DEFINITION_PATH=../data/raw/models/microsoft_building_damage_assessment_cnn_siamese/end_to_end_Siam_UNet.py
ML_MODEL_DEVICE=cpu
COPERNICUS_USERNAME=
COPERNICUS_PASSWORD=
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Untuk frontend, buat file:

```powershell
Set-Content -Path frontend\.env.local -Value "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1"
```

Jika tidak mengisi `TOKENROUTER_API_KEY`, aplikasi tetap jalan, tetapi AI reasoning memakai fallback lokal.

Jika belum menginstall PyTorch, aplikasi tetap jalan memakai `imagery-baseline`. Untuk mengaktifkan inference `SiamUnet` lokal di CPU:

```powershell
cd C:\Users\HP\Laravel\CrisisMap\backend
.\.venv\Scripts\Activate.ps1
pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu
```

Atau gunakan requirements khusus ML CPU:

```powershell
pip install -r requirements-ml-cpu.txt
```

Setelah PyTorch tersedia, restart backend. Status model bisa dicek dari halaman Settings atau endpoint:

```text
GET http://localhost:8000/api/v1/data-sources/status
```

Model TokenRouter yang tersedia di UI:

```text
anthropic/claude-sonnet-4.6
openai/gpt-5.4
moonshotai/kimi-k2.6
google/gemini-3.1-pro-preview
x-ai/grok-4.20-beta
```

## 4. Cara Running Local Manual

Gunakan dua terminal.

### Terminal 1: Backend

```powershell
cd C:\Users\HP\Laravel\CrisisMap\backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Jika PowerShell menolak activate script:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Backend berjalan di:

```text
http://localhost:8000
```

Health check:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected:

```json
{
  "status": "ok"
}
```

### Terminal 2: Frontend

```powershell
cd C:\Users\HP\Laravel\CrisisMap\frontend

npm install
npm run dev
```

Frontend berjalan di:

```text
http://localhost:3000
```

## 5. Cara Running Dengan Docker

Docker Compose tersedia, tetapi untuk development saat ini mode manual lebih mudah untuk debug log.

Jika ingin pakai Docker:

```powershell
cd C:\Users\HP\Laravel\CrisisMap
Copy-Item .env.example .env
docker compose up --build
```

Service:

```text
Frontend: http://localhost:3000
Backend:  http://localhost:8000
Redis:    localhost:6379
PostGIS:  localhost:5432
```

Stop Docker:

```powershell
docker compose down
```

## 6. Cara Stop Local Server Manual

Cek process yang listen di port utama:

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 3000,8000 } |
  Select-Object LocalPort,OwningProcess
```

Stop berdasarkan PID:

```powershell
Stop-Process -Id <PID> -Force
```

Atau jika terminal server masih terbuka, cukup tekan:

```text
Ctrl + C
```

## 7. Cara Testing

### Backend Tests

```powershell
cd C:\Users\HP\Laravel\CrisisMap\backend
.\.venv\Scripts\Activate.ps1
pytest
```

Test backend mencakup:

- `/health`
- create assessment
- live AOI validation
- data-source readiness endpoint
- get assessment detail
- get building GeoJSON
- get report
- get artifacts metadata
- export PDF
- export DOCX
- update analysis settings
- xBD dataset pairing, label parsing, manifest, dan baseline image-change inference

### Frontend Typecheck

```powershell
cd C:\Users\HP\Laravel\CrisisMap\frontend
npm run typecheck
```

### Frontend Production Build

```powershell
cd C:\Users\HP\Laravel\CrisisMap\frontend
npm run build
```

### API Smoke Test Manual

Create assessment:

```powershell
$body = @{
  mode = "demo"
  name = "Manual Beirut Test"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/api/v1/assessments `
  -ContentType "application/json" `
  -Body $body
```

Create live Beirut baseline assessment dengan AOI:

```powershell
$body = @{
  mode = "live"
  name = "Manual Beirut Live Baseline"
  processing_priority = "economy"
  aoi_geojson = @{
    type = "Polygon"
    coordinates = @(
      @(
        @(35.507, 33.895),
        @(35.531, 33.895),
        @(35.531, 33.909),
        @(35.507, 33.909),
        @(35.507, 33.895)
      )
    )
  }
} | ConvertTo-Json -Depth 8

Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/api/v1/assessments `
  -ContentType "application/json" `
  -Body $body
```

Check data-source status:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/data-sources/status
```

Run Alembic migration jika PostGIS aktif:

```powershell
cd C:\Users\HP\Laravel\CrisisMap\backend
.\.venv\Scripts\alembic.exe upgrade head
```

Check xBD dataset status:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/datasets/xbd/status?sample_limit=25
```

Generate xBD manifest sample via API:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/v1/datasets/xbd/manifest?sample_limit=500&write_artifact=true"
```

Generate full manifest via script:

```powershell
cd C:\Users\HP\Laravel\CrisisMap
backend\.venv\Scripts\python.exe scripts\generate_xbd_manifest.py `
  --train-root E:\CrisisMapData\xbd\extracted\train\train `
  --tier3-root E:\CrisisMapData\xbd\extracted\tier3\tier3 `
  --output-dir backend\artifacts `
  --limit 0
```

Run baseline xBD inference sample:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/v1/datasets/xbd/baseline-sample?max_buildings=25"
```

List history:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/assessments
```

Get demo GeoJSON:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/assessments/demo/buildings.geojson
```

Get artifacts:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/assessments/demo/artifacts
```

Download exports:

```powershell
Invoke-WebRequest http://localhost:8000/api/v1/assessments/demo/exports/pdf -OutFile demo.pdf
Invoke-WebRequest http://localhost:8000/api/v1/assessments/demo/exports/docx -OutFile demo.docx
Invoke-WebRequest http://localhost:8000/api/v1/assessments/demo/exports/geojson -OutFile demo.geojson
```

## 8. Tutorial Penggunaan UI

### 8.1 Workspace

URL:

```text
http://localhost:3000/
```

Fungsi:

- Membuat assessment baru.
- Mengatur lokasi/AOI dengan polygon drawing di map.
- Mengatur tanggal event, before imagery range, dan after imagery range.
- Memilih mode `Demo (Beirut)` atau `Live Data`.
- Memilih TokenRouter model.
- Melihat status data source.
- Menjalankan assessment.

Cara pakai:

1. Buka `/`.
2. Pilih `Demo (Beirut)` untuk alur cepat atau `Live Data` untuk baseline inference dari local Maxar imagery.
3. Pastikan default date:
   - Event Date: `2020-08-04`
   - Before: `2020-07-01` sampai `2020-08-03`
   - After: `2020-08-05` sampai `2020-08-15`
4. Pilih TokenRouter model.
5. Untuk live mode, klik `Draw Area manually`, klik minimal tiga titik di map, lalu klik `Use Area`.
6. Klik `Run Assessment`.
7. Jika sukses, user diarahkan ke `/dashboard?assessment=<id>`.

Validasi:

- Before range harus berakhir sebelum event date.
- After range harus mulai setelah event date.
- Live mode wajib punya AOI polygon valid.
- Jika date invalid, status berubah menjadi `Failed`.

Catatan:

- Tombol map tool seperti locate, crosshair, dan draw sudah interaktif untuk UI state.
- Klik kanan saat drawing akan menghapus draft polygon di map.
- Mode demo tetap bisa memakai AOI default Beirut.

### 8.2 Results Dashboard

URL:

```text
http://localhost:3000/dashboard
http://localhost:3000/dashboard?assessment=<assessment_id>
```

Fungsi:

- Melihat hasil assessment di map.
- Melihat building polygon berdasarkan severity.
- Melihat summary stats.
- Mengatur filter infrastructure type.
- Mengatur minimum severity.
- Toggle overlay: buildings, hospitals, roads, utilities, population.
- Melihat priority reconstruction list.
- Masuk ke detail prioritas.

Kontrol utama:

- `Infrastructure Type`: filter asset berdasarkan jenis infrastruktur.
- `Minimum Severity`:
  - `Any`: semua score.
  - `Severe+`: damage score minimal 61.
  - `Critical`: damage score minimal 80.
- `Active Overlays`: mengaktifkan/mematikan layer visual.
- `Reset`: mengembalikan filter ke default.
- `View Full List`: membuka seluruh priority list.

Data yang ditampilkan:

- Buildings assessed.
- Severe/destroyed count.
- Critical infrastructure affected.
- Estimated population impact.
- AI provider/model metadata.

### 8.3 Priority Building Detail

URL:

```text
http://localhost:3000/priority/<building_id>?assessment=<assessment_id>
```

Contoh:

```text
http://localhost:3000/priority/B-1001?assessment=demo
```

Fungsi:

- Melihat detail satu bangunan prioritas.
- Melihat damage score.
- Melihat confidence.
- Melihat humanitarian impact.
- Melihat estimated cost dan repair timeline.
- Melihat required specialists.
- Melihat critical dependencies.
- Download engineering data.
- Mark as assigned.

Kontrol utama:

- `Structural Report`: menuju report view assessment terkait.
- `Engineering Data`: download GeoJSON assessment.
- `Mark as Assigned`: toggle status assignment di UI.

Catatan:

- Preview satellite image di detail saat ini masih visual placeholder.
- Data detail berasal dari priority result backend/demo.

### 8.4 Report View

URL:

```text
http://localhost:3000/reports
http://localhost:3000/reports?assessment=<assessment_id>
```

Fungsi:

- Menampilkan donor summary.
- Menampilkan damage overview.
- Menampilkan top reconstruction priorities.
- Menampilkan phased reconstruction plan.
- Menampilkan engineering dan AI notes.
- Export PDF, DOCX, dan GeoJSON.

Export:

```text
PDF:     /api/v1/assessments/<id>/exports/pdf
DOCX:    /api/v1/assessments/<id>/exports/docx
GeoJSON: /api/v1/assessments/<id>/exports/geojson
```

Catatan:

- PDF dan DOCX saat ini dibuat backend dari assessment/report object.
- GeoJSON berisi building polygons dan damage properties.

### 8.5 Job History

URL:

```text
http://localhost:3000/history
```

Fungsi:

- Melihat daftar assessment.
- Search by name, location, atau assessment ID.
- Filter status.
- Filter last 30 days atau all dates.
- Open completed result.
- Re-run assessment.
- Pagination.

Kontrol utama:

- Search input.
- `Last 30 Days` / `All Dates`.
- Status dropdown.
- Re-run icon.
- `Open Result`.
- Pagination previous/next.

Catatan:

- Backend menyimpan assessment ke PostGIS jika database aktif. Jika tidak aktif, backend otomatis memakai `backend/artifacts/assessments.json`.
- Beberapa row demo tambahan ditampilkan untuk memperlihatkan state running/failed.

### 8.6 Settings

URL:

```text
http://localhost:3000/settings
```

Fungsi:

- Melihat provider status.
- Melihat status PostGIS, OSM/Overpass, HDX, Maxar imagery, xBD, TokenRouter, dan Sentinel credentials.
- Mengubah analysis model profile.
- Mengubah TokenRouter model.
- Mengubah processing priority.
- Mengubah confidence threshold.
- Mengatur auto-publish destroyed tags.
- Mengatur raw imagery retention.
- Mengatur metadata scrub on export.
- Mengelola UI team member state.

Kontrol utama:

- `TokenRouter Model`: memilih model reasoning.
- `Processing Priority`: economy, standard, critical.
- `Confidence Threshold`: 50 sampai 99.
- `Auto-publish 'Destroyed' structural tags`.
- `Save Changes`.
- `Invite`, role selector, suspend/reactivate team member.

Catatan keamanan:

- Raw API key tidak pernah ditampilkan ke frontend.
- UI hanya menampilkan provider status: configured atau missing key.

### 8.7 Docs

URL:

```text
http://localhost:3000/docs
```

Fungsi:

- Navigasi cepat ke Workspace, Dashboard, Reports, Settings, dan History.
- Ringkasan singkat fungsi setiap bagian.

## 9. Backend API

Base URL:

```text
http://localhost:8000/api/v1
```

Endpoint:

| Method | Endpoint | Fungsi |
|---|---|---|
| `POST` | `/assessments` | Membuat assessment baru |
| `GET` | `/assessments` | Mengambil assessment history |
| `GET` | `/assessments/{id}` | Mengambil detail assessment |
| `GET` | `/assessments/{id}/buildings.geojson` | Mengambil building damage GeoJSON |
| `GET` | `/assessments/{id}/priorities` | Mengambil daftar prioritas |
| `GET` | `/assessments/{id}/report` | Mengambil report JSON |
| `GET` | `/assessments/{id}/artifacts` | Mengambil metadata artifacts/chips/validation/exports |
| `GET` | `/assessments/{id}/exports/pdf` | Export PDF |
| `GET` | `/assessments/{id}/exports/docx` | Export DOCX |
| `GET` | `/assessments/{id}/exports/geojson` | Export GeoJSON |
| `GET` | `/data-sources/status` | Mengambil status PostGIS, OSM, HDX, imagery, xBD, TokenRouter, Sentinel |
| `GET` | `/settings/analysis` | Mengambil analysis settings |
| `PATCH` | `/settings/analysis` | Update analysis settings |

Response envelope umum:

```json
{
  "success": true,
  "message": "Assessment retrieved",
  "data": {},
  "meta": {},
  "errors": null
}
```

GeoJSON/export endpoint dapat mengembalikan native file format, bukan envelope JSON.

## 10. Alur Sistem Saat Ini

```mermaid
flowchart TD
    A["User opens Workspace"] --> B["Configure AOI, dates, mode, model"]
    B --> C["Draw AOI polygon for live mode"]
    C --> D["Click Run Assessment"]
    D --> E["POST /api/v1/assessments"]
    E --> F{"Assessment mode"}
    F --> G["Demo: Copernicus EMSR452 or fixture fallback"]
    F --> H["Live: Maxar pre/post + footprints image-change baseline"]
    G --> I["Damage tier and priority preparation"]
    H --> I
    I --> J["TokenRouter reasoning if key exists"]
    I --> K["Heuristic fallback if TokenRouter unavailable"]
    J --> L["Persist to PostGIS or JSON fallback"]
    K --> L
    L --> M["Dashboard fetches assessment, GeoJSON, priorities"]
    M --> N["Reports, artifacts, and exports"]
```

## 11. Alur Real Imagery Beirut

Data real sudah tersedia di `data/raw/`. Pipeline live saat ini sudah menjalankan baseline image-change. Target berikutnya adalah mengganti scoring deterministic dengan model xBD/xView2 fine-tuned.

```mermaid
flowchart TD
    A["Maxar Beirut pre-event GeoTIFF"] --> C["Align, clip AOI, tile/chip generation"]
    B["Maxar Beirut post-event GeoTIFF"] --> C
    D["Building footprints: Maxar + OSM"] --> E["Generate building-level chips"]
    C --> E
    F["Current: deterministic image-change baseline"] --> G["Damage inference per building"]
    F2["Next: xBD/xView2 fine-tuned model"] --> G
    E --> G
    G --> H["Join prediction to building polygon"]
    I["Copernicus EMSR452 ground truth"] --> J["Validation metrics"]
    H --> J
    K["WorldPop"] --> L["Population exposure"]
    M["HDX healthsites + OSM infrastructure"] --> N["Critical infrastructure scoring"]
    H --> O["Priority scoring"]
    L --> O
    N --> O
    O --> P["TokenRouter reasoning and report"]
    P --> Q["Dashboard, detail, exports"]
```

## 12. Data Yang Sudah Tersedia Lokal

Lihat detail lengkap di:

```text
data/DOWNLOADS.md
data/public_data_download_manifest.json
```

Ringkasan:

- Maxar Beirut pre/post imagery.
- OpenAerialMap UAV post-event image.
- Maxar building footprints.
- OSM AOI infrastructure.
- Copernicus EMSR452 ground truth.
- HDX Lebanon healthsites.
- WorldPop Lebanon 2020 population metadata index.
- Microsoft Siamese CNN baseline weights.
- xBD/xView2 Challenge training set dan additional Tier3 training data di `E:\CrisisMapData\xbd\extracted`.

Data manual yang masih belum wajib untuk tahap ini:

- Copernicus Data Space full Sentinel products jika ingin live Sentinel downloader.
- ACLED API data jika ingin conflict-event scoring.
- Commercial imagery tambahan di luar Maxar/OpenAerialMap public data.

## 13. Manual Browser Test Checklist

Saat server berjalan, test desktop browser:

- `/`
  - Mode Demo/Live bisa diganti.
  - Location input bisa diedit.
  - Date input validasi bekerja.
  - Draw area bisa membuat polygon, menampilkan area/vertex, clear, dan memblok live run jika invalid.
  - Map tool locate/crosshair/draw bekerja.
  - Data source row bisa dipilih.
  - TokenRouter model dropdown bisa diganti.
  - Run Assessment membuat assessment dan redirect ke dashboard.
  - Live Data menghasilkan `pipeline: imagery-baseline` jika Maxar imagery dan footprints tersedia.

- `/dashboard`
  - Map muncul.
  - Severity filter bekerja.
  - Infrastructure type filter bekerja.
  - Overlay toggle berubah.
  - Reset filter bekerja.
  - View Full List bekerja.
  - Priority card membuka detail.

- `/priority/B-1001`
  - Detail tampil.
  - Structural Report link membuka Reports.
  - Engineering Data download GeoJSON.
  - Mark as Assigned toggle bekerja.

- `/reports`
  - Donor summary tampil.
  - Top priorities tampil.
  - PDF export berhasil.
  - DOCX export berhasil.
  - GeoJSON export berhasil.

- `/history`
  - Search bekerja.
  - Status filter bekerja.
  - Date range toggle bekerja.
  - Re-run membuat assessment baru.
  - Open Result membuka dashboard.
  - Pagination bekerja.

- `/settings`
  - TokenRouter model selector bekerja.
  - Confidence slider dan number input clamp 50-99.
  - Priority segmented control bekerja.
  - Checkbox bekerja.
  - Save Changes memanggil backend.
  - Invite team member bekerja.
  - Select member, role change, suspend/reactivate bekerja.

## 14. Troubleshooting

### Frontend tidak bisa akses backend

Pastikan backend hidup:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Pastikan frontend env:

```text
frontend/.env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

Restart frontend setelah mengubah env.

### CORS error

Pastikan backend env:

```env
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Restart backend.

### TokenRouter tidak jalan

Cek:

- `backend/.env` punya `TOKENROUTER_API_KEY`.
- Key masih valid.
- `TOKENROUTER_BASE_URL=https://api.tokenrouter.com/v1`.
- Model yang dipilih tersedia di provider.

Jika gagal, backend fallback ke local heuristic agar assessment tetap selesai.

### Port sudah dipakai

Cek port:

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 3000,8000 }
```

Stop PID:

```powershell
Stop-Process -Id <PID> -Force
```

### Data raw tidak ada

Jalankan ulang downloader:

```powershell
cd C:\Users\HP\Laravel\CrisisMap
powershell -ExecutionPolicy Bypass -File .\scripts\download_public_beirut_data.ps1
```

## 15. Batasan Saat Ini

Untuk mencegah salah paham:

- CrisisMap sudah bisa menjalankan baseline image-change dari Maxar GeoTIFF lokal, tetapi belum memakai deep learning model fine-tuned xBD.
- xBD/xView2 sudah dipasang untuk registry/manifest/preprocessing/sample baseline, tetapi belum dipakai untuk training/fine-tuning production model.
- PostGIS sudah didukung lewat SQLAlchemy/Alembic, tetapi jika database lokal tidak hidup backend akan fallback ke JSON store.
- Live OSM adapter bisa memakai Overpass jika cache lokal tidak tersedia, tetapi Sentinel full-product download masih menunggu credential Copernicus.
- Priority reasoning sudah membaca hasil assessment backend; TokenRouter tetap hanya untuk reasoning/report, bukan pixel-level damage detection.

Tahap berikutnya agar benar-benar real:

1. Fine-tune/evaluate model xBD/xView2 di Kaggle/Colab.
2. Export model ke format yang bisa diload backend.
3. Ganti deterministic image-change scoring dengan model inference.
4. Tambahkan WorldPop raster GeoTIFF untuk exposure sampling per AOI/building.
5. Tambahkan ACLED/Copernicus credentials jika dibutuhkan.
6. Hitung validation metric penuh terhadap EMSR452/UNOSAT-like ground truth.
