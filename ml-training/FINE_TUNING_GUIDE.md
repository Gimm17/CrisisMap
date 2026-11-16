# CrisisMap Fine-Tuning Guide

Panduan lengkap dan beginner-friendly untuk fine-tuning model SiamUnet pada CrisisMap.

## Daftar Isi

1. [Apa Itu Fine-Tuning?](#1-apa-itu-fine-tuning)
2. [Mengapa SiamUnet?](#2-mengapa-siamunet)
3. [Arsitektur SiamUnet](#3-arsitektur-siamunet)
4. [Data: xBD Challenge Format](#4-data-xbd-challenge-format)
5. [Preprocessing Parity](#5-preprocessing-parity)
6. [Strategi Training 2-Stage](#6-strategi-training-2-stage)
7. [Menjalankan di Kaggle](#7-menjalankan-di-kaggle)
8. [Evaluasi & Metrik](#8-evaluasi--metrik)
9. [Integrasi Backend](#9-integrasi-backend)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Apa Itu Fine-Tuning?

**Fine-tuning** = mengambil model yang sudah dilatih (pre-trained) dan melatih ulang pada data yang lebih spesifik.

```
Pre-trained Checkpoint          Fine-tuned Checkpoint
(Microsoft, xBD general)        (CrisisMap, Beirut-specific)
┌────────────────────┐          ┌────────────────────┐
│ epoch: 279         │          │ epoch: 35+         │
│ best_f1: 0.6227    │  ────►   │ best_f1: 0.55+     │
│ 19 disaster types  │  train   │ Optimized for      │
│ General weights    │          │ Beirut domain      │
└────────────────────┘          └────────────────────┘
```

**Mengapa tidak train from scratch?**
- Model sudah "tahu" fitur visual bangunan dari 279 epoch training
- Fine-tuning lebih cepat (15-35 epoch vs 200+ epoch)
- Butuh lebih sedikit data
- Risiko overfitting lebih rendah

---

## 2. Mengapa SiamUnet?

| Kriteria | SiamUnet ✅ | YOLO ❌ | KNN ❌ | MobileNetV2 ⚠️ |
|----------|------------|---------|--------|----------------|
| Input | 2 gambar (pre+post) | 1 gambar | Vektor fitur | 1 gambar |
| Output | Pixel mask 5-class | Bounding box | Label per instance | Class probability |
| Change detection | ✅ Native | ❌ Single-frame | ❌ | ❌ |
| Backend compatible | ✅ 100% | ❌ 0% | ❌ 0% | ❌ Breaks state_dict |

**Kesimpulan:** SiamUnet adalah satu-satunya arsitektur yang (a) mendukung change detection pre/post, (b) output pixel-level mask, dan (c) kompatibel dengan backend CrisisMap yang sudah ada.

---

## 3. Arsitektur SiamUnet

```
                    ┌─────────────────────────────────────────┐
                    │           SIAMESE U-NET                  │
                    │                                          │
  Pre-disaster ──► │  ┌─────────┐    ┌─────────┐             │ ──► Seg Pre  (2 class)
  (3,256,256)      │  │ Encoder │───►│ Decoder │──► conv_s   │
                    │  │ (shared)│    │         │             │
  Post-disaster ─► │  │         │───►│         │──► conv_s   │ ──► Seg Post (2 class)
  (3,256,256)      │  └────┬────┘    └─────────┘             │
                    │       │                                  │
                    │  ┌────▼────┐                             │
                    │  │ DIFF    │  enc_post - enc_pre         │
                    │  │ (subtract each level)                 │
                    │  └────┬────┘                             │
                    │  ┌────▼────┐                             │
                    │  │ Damage  │                             │
                    │  │Classifier──► conv_c                   │ ──► Damage  (5 class)
                    │  └─────────┘                             │
                    └─────────────────────────────────────────┘
```

### Output Shapes (Verified)

| Output | Shape | Classes |
|--------|-------|---------|
| `seg_pre` | `(B, 2, H, W)` | background, building |
| `seg_post` | `(B, 2, H, W)` | background, building |
| `damage` | `(B, 5, H, W)` | background, no-damage, minor, major, destroyed |

### Layer Groups (untuk Freeze Logic)

**Segmentation Arm (64 parameters):**
`encoder1-4`, `bottleneck`, `pool1-4`, `upconv1-4`, `decoder1-4`, `conv_s`

**Damage Classifier Arm (34 parameters):**
`upconv1_c-4_c`, `conv1_c-4_c`, `conv_c`

---

## 4. Data: xBD Challenge Format

### Apa yang KITA pakai

| Dataset | Pairs | Size | Format |
|---------|------:|-----:|--------|
| xBD Train | 2,799 | 7.8 GB | PNG 1024×1024 + JSON + target PNG |
| xBD Tier3 | 6,369 | 17.3 GB | PNG 1024×1024 + JSON (NO targets) |
| **Total** | **9,168** | **25.1 GB** | xView2 Challenge format |

### Apa yang TIDAK kita pakai
- ❌ GeoTIFF 51 GB version (disk tidak muat)
- ❌ xBD test set (tidak punya label)
- ❌ xBD hold set

### Struktur Folder Aktual

```
E:\CrisisMapData\xbd\extracted\
├── train\train\
│   ├── images\    5,598 PNG  (2,799 pre + 2,799 post)
│   ├── labels\    5,598 JSON (2,799 pre + 2,799 post)
│   └── targets\   5,598 PNG  (pre-computed masks)
└── tier3\tier3\
    ├── images\    12,738 PNG (6,369 pre + 6,369 post)
    └── labels\    12,738 JSON
    ⚠️ TIDAK ADA targets/ → harus rasterize dari JSON
```

### Label JSON Structure

**Post-disaster** (memiliki damage subtype):
```json
{
  "features": {
    "xy": [
      {
        "properties": {
          "feature_type": "building",
          "subtype": "no-damage"    // damage class
        },
        "wkt": "POLYGON ((x1 y1, x2 y2, ...))"  // pixel coords
      }
    ]
  },
  "metadata": {
    "disaster": "guatemala-volcano",
    "gsd": 1.4085,
    "original_width": 1024
  }
}
```

**Pre-disaster** (TANPA damage subtype — hanya segmentation):
```json
{
  "features": {
    "xy": [
      {
        "properties": {
          "feature_type": "building"
          // TIDAK ADA "subtype"
        }
      }
    ]
  }
}
```

---

## 5. Preprocessing Parity

### ATURAN KRITIS

> Training preprocessing **HARUS** menghasilkan tensor yang kompatibel dengan inference backend.
> Kalau beda, validation metrics bagus tapi **jeblok saat deploy**.

### Pemetaan Eksplisit

```python
# === TRAINING (xBD PNG) ===
img = Image.open(path).convert("RGB")        # RGB
arr = np.array(img, dtype=np.float32) / 255.0 # normalize [0,1]
tensor = arr.transpose(2, 0, 1)              # (3, 256, 256)

# === BACKEND INFERENCE (Beirut GeoTIFF) ===
data = src.read(indexes=[1, 2, 3])           # RGB
data = data.astype("float32")
scale = max(np.percentile(data, 99), 255.0)  # adaptive scale
data = np.clip(data / scale, 0.0, 1.0)       # normalize [0,1]
```

**Mengapa sedikit berbeda?**
- xBD PNG = 8-bit → max = 255 → p99 ≈ 255 → **identik**
- Beirut GeoTIFF = 11-16 bit → p99 bisa > 255 → **domain shift**
- Perbedaan ini SENGAJA — Stage B calibration menjembataninya

---

## 6. Strategi Training 2-Stage

### Stage A: Fine-tune di xBD (General Damage)

```
┌──────────────────────────────────────────────────────────────────┐
│                         STAGE A                                   │
│                                                                   │
│  ┌──────────────┐        ┌──────────────┐        ┌────────────┐ │
│  │   Phase 1     │        │   Phase 2     │        │  Evaluate  │ │
│  │  Segmentation │  ────► │    Damage     │  ────► │  Test Set  │ │
│  │   15 epochs   │        │   20 epochs   │        │  xBD val   │ │
│  │   lr=1e-4     │        │   lr=5e-5     │        │            │ │
│  │               │        │               │        │  Target:   │ │
│  │ Freeze: dmg   │        │ Freeze: seg   │        │  F1≥0.55   │ │
│  │ Train: seg    │        │ Train: dmg    │        │            │ │
│  └──────────────┘        └──────────────┘        └────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

**Phase 1 — Building Segmentation:**
- Tujuan: model belajar mendeteksi bangunan dari pre/post imagery
- Loss: `weights_loss = [0.5, 0.5, 0.0]` (hanya segmentation)
- Freeze: semua damage classifier layers
- Metric: validation IoU

**Phase 2 — Damage Classification:**
- Tujuan: model belajar mengklasifikasi tingkat kerusakan
- Loss: `weights_loss = [0.0, 0.0, 1.0]` (hanya damage)
- Freeze: semua segmentation layers
- Metric: validation macro F1
- Class weights: `[0.05, 0.10, 0.60, 0.80, 1.00]` (upweight rare classes)

### Stage B: Kalibrasi Beirut (Domain Adaptation)

```
┌──────────────────────────────────────────────────────────────────┐
│                         STAGE B                                   │
│                                                                   │
│  Load Stage A    ──►  Fine-tune damage    ──►  Evaluate on       │
│  best checkpoint      classifier only          HELD-OUT test     │
│                       lr=1e-5 (micro)          (NEVER trained)   │
│                       ~10 epochs                                  │
│                       Beirut Maxar chips        Report F1 HERE   │
└──────────────────────────────────────────────────────────────────┘
```

**Anti-Leakage Rules (Poin 6):**
- Held-out test set **NEVER** dipakai untuk kalibrasi
- Tidak boleh overlap dengan 60 buildings di ASM-D06926
- "Possibly Damaged" **EXCLUDED** dari training (uncertain)

---

## 7. Menjalankan di Kaggle

### Langkah Persiapan

1. **Buat Kaggle Account** → Enable GPU
2. **Upload xBD sebagai Private Dataset:**
   - Nama: `xbd-xview2-challenge`
   - Upload `train_images_labels_targets.tar.gz` + `tier3.tar.gz`
   - Kaggle auto-extracts into mount path
3. **Upload checkpoint sebagai Dataset:**
   - Nama: `crisismap-checkpoint`
   - Upload `model_best.pth.tar`

### Menjalankan Notebook

1. New Notebook → Settings → Accelerator: **GPU P100**
2. Right panel → Add Data → Select both datasets
3. Upload `01_finetune_xbd.ipynb`
4. **Run All** (Shift+Enter per cell atau Run All)
5. Monitor progress di output cells
6. Download `output/model_best.pth.tar` setelah selesai

### Estimasi Waktu

| Phase | Batches/epoch | Epochs | ~Time |
|-------|:------------:|:------:|:-----:|
| Phase 1 | ~460 | 15 | ~1.5h |
| Phase 2 | ~460 | 20 | ~2.5h |
| Evaluation | ~60 | 1 | ~0.2h |
| **Total** | | | **~4.2h** |

> Dengan `subsample_tier3=0.5`. Full run (~8h) mungkin perlu 2 session Kaggle.

### Checkpoint Resume

Jika Kaggle session terputus:
1. Buka Notebook Output folder
2. Cari `checkpoint_step*.pth.tar` terakhir
3. Upload sebagai dataset baru
4. Modifikasi Cell 8 untuk load checkpoint ini
5. Skip Phase 1 jika sudah selesai

---

## 8. Evaluasi & Metrik

### Pixel-Level vs Building-Level (Poin 5)

| Level | Untuk Apa | Cara Hitung |
|-------|-----------|-------------|
| **Pixel-level** | Training loss optimization | Per-pixel argmax → F1 per class |
| **Building-level** | Journal reporting, EMSR452 comparison | Average softmax over building footprint → argmax |

**Backend menggunakan building-level:**
```python
# ml_inference.py line 75
probs = torch.softmax(damage_logits, dim=1).mean(dim=(0, 2, 3))
```

### Target Metrik

| Metrik | Baseline (Zero-Shot) | Target Stage A | Target Stage B |
|--------|:-------------------:|:-------------:|:--------------:|
| Macro F1 (xBD val) | — | **≥ 0.55** | — |
| Macro F1 (Beirut) | 0.221 | ≥ 0.40 | **≥ 0.50** |
| Per-class F1 (destroyed) | ~0 | ≥ 0.45 | ≥ 0.50 |

### Visualisasi yang Dihasilkan

1. **Loss curves** — train vs val per epoch (Phase 1 + Phase 2)
2. **Confusion matrix** — heatmap 5×5 class (normalized by row)
3. **Per-class F1** — bar chart comparing all 4 damage classes
4. **Sample predictions** — pre/post image + ground truth vs prediction overlay
5. **ROC curves** — one-vs-rest dengan AUC per class

---

## 9. Integrasi Backend

### Setelah Training Selesai

```bash
# 1. Download checkpoint dari Kaggle
#    → output/model_best.pth.tar

# 2. Copy ke backend
cp model_best.pth.tar \
   data/raw/models/microsoft_building_damage_assessment_cnn_siamese/model_finetuned.pth.tar

# 3. Update .env
echo 'ML_MODEL_CHECKPOINT_PATH=../data/raw/models/microsoft_building_damage_assessment_cnn_siamese/model_finetuned.pth.tar' >> .env

# 4. Restart backend
cd backend && uvicorn app.main:app --reload
```

### Verifikasi

1. Buat assessment baru via UI (live mode)
2. Cek response JSON: `"inference_method": "ml-inference"` harus muncul
3. Bandingkan macro F1 sebelum vs sesudah di `ML_INFERENCE_REPORT.md`

### Checkpoint Compatibility Requirements

| Requirement | Detail |
|-------------|--------|
| Format | `.pth.tar` (Python dict) |
| Key weights | `'state_dict'` (bukan `'model'` atau `'model_state_dict'`) |
| Key prefix | TIDAK ADA `'module.'` atau `'model.'` |
| state_dict keys | 176 (harus cocok persis dengan `SiamUnet()`) |
| Load method | `torch.load(path, map_location="cpu")` |
| Strict mode | `model.load_state_dict(sd, strict=False)` — backend tolerant |

---

## 10. Troubleshooting

### "CUDA out of memory"
- Kurangi `batch_size` dari 16 ke 8
- Enable `gradient_accumulation_steps: 2` di config
- Pastikan `num_workers` ≤ 2 (Kaggle limitation)

### "No module named ..."
- Notebook self-contained — semua utilities diinline
- Tidak perlu install tambahan di Kaggle

### "Kaggle session timeout"
- Checkpoint otomatis disave setiap 500 steps
- Lihat bagian "Checkpoint Resume" di atas

### "val_f1 rendah padahal train_loss turun"
- Cek class imbalance — majority class (no-damage) mendominasi
- Tingkatkan `class_weights_dmg` untuk kelas minoritas
- Pastikan tidak ada data leakage (split harus per TILE)

### "F1 bagus di xBD tapi jeblok di Beirut"
- Ini domain shift — jalankan Stage B
- Periksa preprocessing parity (normalization harus match)
- Cek GSD perbedaan antara xBD tiles dan Beirut Maxar

### "state_dict mismatch saat load di backend"
- Pastikan TIDAK pakai `DataParallel` saat save
- Cek: `any(k.startswith('module.') for k in sd)` harus `False`
- Jika True, strip: `{k.replace('module.', ''): v for k, v in sd.items()}`
