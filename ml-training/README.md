# CrisisMap ML Training Workspace

Reproducible machine learning pipeline to fine-tune the Microsoft SiamUnet checkpoint for building damage assessment, targeting the Beirut 2020 port explosion.

## Quick Start (Kaggle)

### Prerequisites
1. **Kaggle account** with GPU access enabled
2. **xBD dataset** uploaded as a private Kaggle Dataset (~25 GB):
   - `train_images_labels_targets.tar.gz` (7.8 GB, 2,799 tile pairs)
   - `tier3.tar.gz` (17.3 GB, 6,369 tile pairs)
3. **Existing checkpoint** `model_best.pth.tar` (Microsoft/NLRC 510)

### Upload Data to Kaggle
1. Go to [kaggle.com/datasets](https://www.kaggle.com/datasets) → **New Dataset**
2. Name it `xbd-xview2-challenge`
3. Upload both `.tar.gz` files (Kaggle auto-extracts)
4. Expected mount paths after extraction:
   ```
   /kaggle/input/xbd-xview2-challenge/train/train/{images,labels,targets}/
   /kaggle/input/xbd-xview2-challenge/tier3/tier3/{images,labels}/
   ```
5. Create a second dataset `crisismap-checkpoint` with `model_best.pth.tar`

### Run Stage A
1. Create a new Kaggle Notebook → **GPU P100** or **T4 x2**
2. Add both datasets in the right panel
3. Upload `notebooks/01_finetune_xbd.ipynb`
4. Run all cells sequentially
5. Download `output/model_best.pth.tar` when complete

### Run Stage B (Optional)
1. Upload the Stage A checkpoint as a Kaggle Dataset
2. Upload Beirut Maxar imagery + EMSR452 ground truth
3. Run `notebooks/02_calibrate_beirut.ipynb`

## Directory Structure

```
ml-training/
├── README.md                          ← This file
├── FINE_TUNING_GUIDE.md               ← Detailed guide with ML concepts
├── requirements.txt                   ← Pinned dependencies
├── configs/
│   └── training_config.yaml           ← All hyperparameters (single source of truth)
├── notebooks/
│   ├── 01_finetune_xbd.ipynb          ← Stage A: fine-tune on xBD (Kaggle)
│   └── 02_calibrate_beirut.ipynb      ← Stage B: domain calibration (Kaggle)
├── utils/                             ← Helper modules imported by notebooks
│   ├── __init__.py
│   ├── dataset.py                     ← XBDPatchDataset, tile discovery, rasterization
│   ├── transforms.py                  ← Normalization & augmentation
│   ├── metrics.py                     ← Pixel-level & building-level metrics, ROC
│   └── visualization.py              ← Loss curves, confusion matrix, sample plots
└── scratch/                           ← Temporary verification scripts
```

## Data Format (xView2 Challenge)

The pipeline expects **xView2 Challenge format** (NOT GeoTIFF):

| Folder | Format | Content |
|--------|--------|---------|
| `images/` | PNG 1024×1024, 8-bit RGB | Satellite imagery |
| `labels/` | JSON with WKT polygons | Building footprints + damage subtype |
| `targets/` | PNG 1024×1024, 8-bit | Pre-computed target masks (train only) |

**Naming convention:** `{disaster}_{tile_id}_{pre|post}_disaster.{png|json}`

> **Important:** Tier3 does NOT have a `targets/` folder. The dataset loader rasterizes masks from JSON polygons for all data, ensuring consistency.

## Verified Data (Actual Counts)

| Split | Tile Pairs | Images | Labels | Targets |
|-------|-----------|--------|--------|---------|
| **Train** | 2,799 | 5,598 | 5,598 | 5,598 |
| **Tier3** | 6,369 | 12,738 | 12,738 | ❌ None |
| **Total** | **9,168** | 18,336 | 18,336 | 5,598 |

## Training Strategy

```
Phase 1 (Segmentation)          Phase 2 (Damage Classification)
┌─────────────────────┐        ┌─────────────────────┐
│ Train: encoder +    │        │ Train: damage       │
│   decoder + conv_s  │  ───►  │   classifier arm    │
│ Freeze: damage arm  │        │ Freeze: everything  │
│ Loss: [0.5,0.5,0]   │        │   else              │
│ 15 epochs, lr=1e-4  │        │ Loss: [0,0,1]       │
└─────────────────────┘        │ 20 epochs, lr=5e-5  │
                               └─────────────────────┘
```

## Backend Integration

The fine-tuned checkpoint is **drop-in compatible** with `ml_inference.py`:

1. Copy `model_best.pth.tar` to `data/raw/models/microsoft_building_damage_assessment_cnn_siamese/`
2. Update `.env`:
   ```
   ML_MODEL_CHECKPOINT_PATH=../data/raw/models/microsoft_building_damage_assessment_cnn_siamese/model_best.pth.tar
   ```
3. Restart backend: `uvicorn app.main:app --reload`

### Checkpoint Format (MUST match backend)
```python
{
    'epoch': int,
    'state_dict': model.state_dict(),   # RAW keys, NO 'module.' prefix
    'optimizer': optimizer.state_dict(),
    'val_f1_avg': float,
    'best_f1': float,
}
```

The backend loads via:
- `checkpoint.get('state_dict')` → extract weights
- `model.load_state_dict(state_dict, strict=False)` → load into SiamUnet
- `map_location="cpu"` → CPU inference

## Preprocessing Parity

| Aspect | Training (xBD PNG) | Backend Inference (Beirut GeoTIFF) |
|--------|-------------------|------------------------------------|
| Band order | RGB | `indexes=[1,2,3]` = RGB |
| Chip size | 256×256 (crop) | 256×256 (resize) |
| Normalize | `/255.0` → [0,1] | `/max(p99, 255.0)` → [0,1] |
| Data type | float32 | float32 |

> The normalization difference is part of the domain shift addressed by Stage B.

## Compute Notes (Kaggle Free Tier)

- **GPU:** P100 (16 GB) or T4 x2 — 12 hour session limit
- **Tier3 subsampling:** Default 50% to fit in one session (~6h estimated)
- **Checkpoint resume:** Saves every 500 steps for session safety
- **Full run:** Set `subsample_tier3: 1.0` in config (may need 2 sessions)

## Reproducibility

- All random seeds pinned (`seed=42`)
- Requirements version-pinned in `requirements.txt`
- `state_dict` portable: GPU → CPU via `map_location="cpu"`
- Compatible with PyTorch 2.0+ (backend uses 2.5.1)

## Keterbatasan Penelitian / Future Work

> Items below are **documented limitations**, NOT blockers.

1. **Single model (no ensemble):** xView2 top submissions used ensembles (F1~0.80). Single SiamUnet realistic target: F1~0.55-0.65.
2. **No full GeoTIFF dataset:** 51 GB GeoTIFF version not used (disk constraint). Challenge PNG format used instead.
3. **Limited Beirut ground truth:** EMSR452 provides limited buildings. Stage B calibration uses what's available.
4. **Possibly Damaged excluded:** EMSR452 "Possibly Damaged" grade is ambiguous — excluded from training per Poin 6 to protect validity.
5. **Future:** MobileNetV2 backbone swap, multi-scale inference, temporal attention mechanisms.
