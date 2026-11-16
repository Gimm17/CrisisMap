"""
XBD Challenge Dataset Loader for CrisisMap ML Fine-Tuning.

Handles the xView2 CHALLENGE format:
  - images/: PNG 1024x1024, 8-bit RGB
  - labels/: JSON with polygon annotations (WKT) + damage subtype
  - targets/: Pre-computed target mask PNGs (train only, NOT tier3)

Naming convention:
  {disaster}_{tile_id}_{pre|post}_disaster.{png|json}

Key design decisions:
  1. Rasterize polygons from JSON (not rely on targets/ which tier3 lacks)
  2. Split by TILE (not patch) to prevent data leakage
  3. Preprocessing matches backend ml_inference.py: RGB, /255.0, [0,1]
  4. Stratified split by disaster_type for balanced representation

Author: CrisisMap Research Team
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset

# ---------------------------------------------------------------------------
# Damage label mapping (from xBD JSON subtype to integer class index)
# ---------------------------------------------------------------------------
DAMAGE_LABEL_MAP = {
    "un-classified": 0,   # background / no annotation
    "no-damage": 1,
    "minor-damage": 2,
    "major-damage": 3,
    "destroyed": 4,
}

# xBD tile naming regex: {disaster}_{tile_id}_{pre|post}_disaster
TILE_PATTERN = re.compile(
    r"^(?P<disaster>.+?)_(?P<tile_id>\d+)_(?P<phase>pre|post)_disaster$"
)


def parse_tile_name(filename: str) -> dict[str, str] | None:
    """Parse an xBD filename into components.

    Args:
        filename: e.g. 'guatemala-volcano_00000000_post_disaster.png'

    Returns:
        dict with keys: disaster, tile_id, phase, stem
        or None if pattern doesn't match
    """
    stem = Path(filename).stem
    match = TILE_PATTERN.match(stem)
    if not match:
        return None
    return {
        "disaster": match.group("disaster"),
        "tile_id": match.group("tile_id"),
        "phase": match.group("phase"),
        "stem": stem,
    }


def discover_tile_pairs(
    data_root: str | Path,
    images_dir: str = "images",
    labels_dir: str = "labels",
) -> list[dict[str, Any]]:
    """Discover all valid pre/post tile pairs in an xBD directory.

    A valid pair requires:
      - {disaster}_{id}_pre_disaster.png  in images/
      - {disaster}_{id}_post_disaster.png in images/
      - {disaster}_{id}_post_disaster.json in labels/ (for damage subtype)

    Args:
        data_root: Path to xBD split root (e.g. .../train/train)
        images_dir: Subdirectory name for images
        labels_dir: Subdirectory name for labels

    Returns:
        List of dicts, each containing paths and metadata for a tile pair
    """
    root = Path(data_root)
    img_dir = root / images_dir
    lbl_dir = root / labels_dir

    if not img_dir.exists():
        raise FileNotFoundError(f"Images directory not found: {img_dir}")
    if not lbl_dir.exists():
        raise FileNotFoundError(f"Labels directory not found: {lbl_dir}")

    # Group files by (disaster, tile_id)
    tiles: dict[tuple[str, str], dict[str, Path]] = defaultdict(dict)

    for f in sorted(img_dir.iterdir()):
        if not f.suffix.lower() == ".png":
            continue
        parsed = parse_tile_name(f.name)
        if parsed is None:
            continue
        key = (parsed["disaster"], parsed["tile_id"])
        tiles[key][f"img_{parsed['phase']}"] = f

    for f in sorted(lbl_dir.iterdir()):
        if not f.suffix.lower() == ".json":
            continue
        parsed = parse_tile_name(f.name)
        if parsed is None:
            continue
        key = (parsed["disaster"], parsed["tile_id"])
        tiles[key][f"lbl_{parsed['phase']}"] = f

    # Filter to complete pairs
    pairs = []
    for (disaster, tile_id), files in sorted(tiles.items()):
        if "img_pre" not in files or "img_post" not in files:
            continue
        if "lbl_post" not in files:
            continue  # need post label for damage subtype
        pairs.append({
            "disaster": disaster,
            "tile_id": tile_id,
            "img_pre": files["img_pre"],
            "img_post": files["img_post"],
            "lbl_pre": files.get("lbl_pre"),    # may be None
            "lbl_post": files["lbl_post"],
        })

    return pairs


def parse_label_json(label_path: Path) -> list[dict[str, Any]]:
    """Parse an xBD label JSON file and extract building polygons.

    Args:
        label_path: Path to .json label file

    Returns:
        List of building dicts with keys:
          - subtype: damage class string (e.g. "no-damage")
          - xy_coords: list of (x, y) tuples in pixel coordinates
    """
    with open(label_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", {})
    xy_features = features.get("xy", [])

    buildings = []
    for feat in xy_features:
        props = feat.get("properties", {})
        if props.get("feature_type") != "building":
            continue

        wkt = feat.get("wkt", "")
        coords = _parse_wkt_polygon(wkt)
        if coords is None or len(coords) < 3:
            continue

        subtype = props.get("subtype", "un-classified")
        buildings.append({
            "subtype": subtype,
            "xy_coords": coords,
        })

    return buildings


def _parse_wkt_polygon(wkt: str) -> list[tuple[float, float]] | None:
    """Parse a WKT POLYGON string into list of (x, y) coordinate tuples.

    Args:
        wkt: WKT string like "POLYGON ((x1 y1, x2 y2, ...))"

    Returns:
        List of (x, y) tuples or None if parsing fails
    """
    try:
        # Extract coordinates between parentheses
        inner = wkt.split("((")[1].split("))")[0]
        coords = []
        for pair in inner.split(","):
            parts = pair.strip().split()
            if len(parts) >= 2:
                coords.append((float(parts[0]), float(parts[1])))
        return coords
    except (IndexError, ValueError):
        return None


def rasterize_buildings(
    buildings: list[dict[str, Any]],
    height: int = 1024,
    width: int = 1024,
    mode: str = "damage",
) -> np.ndarray:
    """Rasterize building polygons into a label mask.

    Args:
        buildings: List from parse_label_json()
        height: Output mask height
        width: Output mask width
        mode: "segmentation" → binary (0=bg, 1=building)
              "damage" → multi-class (0=bg, 1-4=damage classes)

    Returns:
        np.ndarray of shape (height, width) with integer class labels
    """
    from PIL import Image, ImageDraw

    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)

    for bld in buildings:
        coords = bld["xy_coords"]
        if len(coords) < 3:
            continue

        # Convert to flat list of (x, y) for PIL
        flat_coords = [(int(round(x)), int(round(y))) for x, y in coords]

        if mode == "segmentation":
            fill_value = 1  # building = 1
        else:
            subtype = bld.get("subtype", "un-classified")
            fill_value = DAMAGE_LABEL_MAP.get(subtype, 0)

        draw.polygon(flat_coords, fill=fill_value)

    return np.array(mask, dtype=np.int64)


def stratified_split(
    tile_pairs: list[dict[str, Any]],
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    seed: int = 42,
) -> dict[str, list[dict[str, Any]]]:
    """Split tile pairs into train/val/test with stratification by disaster type.

    Split is done at TILE level (not patch level) to prevent data leakage.

    Args:
        tile_pairs: List of tile pair dicts from discover_tile_pairs()
        train_ratio: Fraction for training
        val_ratio: Fraction for validation
        test_ratio: Fraction for testing
        seed: Random seed for reproducibility

    Returns:
        Dict with keys "train", "val", "test" mapping to lists of tile pairs
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, \
        f"Ratios must sum to 1.0, got {train_ratio + val_ratio + test_ratio}"

    rng = np.random.RandomState(seed)

    # Group by disaster type
    by_disaster: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pair in tile_pairs:
        by_disaster[pair["disaster"]].append(pair)

    splits: dict[str, list[dict[str, Any]]] = {"train": [], "val": [], "test": []}

    for disaster, pairs in sorted(by_disaster.items()):
        indices = np.arange(len(pairs))
        rng.shuffle(indices)

        n = len(pairs)
        n_val = max(1, int(round(n * val_ratio)))
        n_test = max(1, int(round(n * test_ratio)))
        n_train = n - n_val - n_test

        if n_train < 1:
            # Too few tiles — put all in train
            n_train = n
            n_val = 0
            n_test = 0

        for i, idx in enumerate(indices):
            if i < n_train:
                splits["train"].append(pairs[idx])
            elif i < n_train + n_val:
                splits["val"].append(pairs[idx])
            else:
                splits["test"].append(pairs[idx])

    return splits


class XBDPatchDataset(Dataset):
    """PyTorch Dataset for xBD tile patches.

    Converts 1024x1024 tiles into 256x256 patches with corresponding labels.

    Preprocessing matches backend ml_inference.py:
      - Band order: RGB (channels 0, 1, 2)
      - Normalize: img / 255.0 → [0, 1] range
      - Shape: (3, 256, 256) float32 tensor

    Args:
        tile_pairs: List of tile pair dicts from discover_tile_pairs()
        patch_size: Size of patches to crop (default 256)
        patches_per_tile: Number of non-overlapping patches per tile (default 16)
        overlap_patches: Number of additional random overlapping patches (default 0)
        augment: Whether to apply data augmentation (default False)
        mode: "both" for seg+damage, "segmentation" for seg only, "damage" for damage only
        seed: Random seed for reproducible overlap patch positions
        use_target_png: Whether to try loading target PNG instead of rasterizing
        targets_dir: Name of targets subfolder (default "targets")
    """

    def __init__(
        self,
        tile_pairs: list[dict[str, Any]],
        patch_size: int = 256,
        patches_per_tile: int = 16,
        overlap_patches: int = 0,
        augment: bool = False,
        mode: str = "both",
        seed: int = 42,
        use_target_png: bool = False,
        targets_dir: str = "targets",
    ):
        self.tile_pairs = tile_pairs
        self.patch_size = patch_size
        self.patches_per_tile = patches_per_tile
        self.overlap_patches = overlap_patches
        self.augment = augment
        self.mode = mode
        self.seed = seed
        self.use_target_png = use_target_png
        self.targets_dir = targets_dir

        # Pre-compute patch positions for non-overlapping grid
        self.grid_size = int(1024 / patch_size)  # 4 for 256
        assert self.grid_size ** 2 == patches_per_tile, \
            f"patches_per_tile={patches_per_tile} must equal grid_size^2={self.grid_size**2}"

        # Generate patch positions
        self._patches_index: list[tuple[int, int, int, int]] = []  # (tile_idx, patch_idx, row, col)
        self._build_patch_index()

    def _build_patch_index(self):
        """Build index mapping dataset indices to (tile, patch) positions."""
        rng = np.random.RandomState(self.seed)

        for tile_idx in range(len(self.tile_pairs)):
            # Non-overlapping grid patches
            for row in range(self.grid_size):
                for col in range(self.grid_size):
                    y = row * self.patch_size
                    x = col * self.patch_size
                    self._patches_index.append((tile_idx, len(self._patches_index), y, x))

            # Random overlapping patches
            for _ in range(self.overlap_patches):
                y = rng.randint(0, 1024 - self.patch_size)
                x = rng.randint(0, 1024 - self.patch_size)
                self._patches_index.append((tile_idx, len(self._patches_index), y, x))

    def __len__(self) -> int:
        return len(self._patches_index)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        tile_idx, _, y, x = self._patches_index[idx]
        pair = self.tile_pairs[tile_idx]

        # Load images
        pre_img = self._load_image(pair["img_pre"])
        post_img = self._load_image(pair["img_post"])

        # Crop patch
        pre_patch = pre_img[:, y:y + self.patch_size, x:x + self.patch_size]
        post_patch = post_img[:, y:y + self.patch_size, x:x + self.patch_size]

        # Load labels
        seg_mask_pre, seg_mask_post, damage_mask = self._load_labels(pair, y, x)

        # Apply augmentation
        if self.augment:
            pre_patch, post_patch, seg_mask_pre, seg_mask_post, damage_mask = \
                self._apply_augmentation(pre_patch, post_patch, seg_mask_pre, seg_mask_post, damage_mask)

        result = {
            "pre": pre_patch,
            "post": post_patch,
            "seg_pre": seg_mask_pre,
            "seg_post": seg_mask_post,
            "damage": damage_mask,
            "disaster": pair["disaster"],
            "tile_id": pair["tile_id"],
        }
        return result

    def _load_image(self, path: Path) -> torch.Tensor:
        """Load PNG image and normalize to [0, 1] float32 tensor.

        Preprocessing matches backend:
          - RGB band order
          - Divide by 255.0 → [0, 1]
          - Shape: (3, H, W)
        """
        img = Image.open(path).convert("RGB")
        arr = np.array(img, dtype=np.float32)  # (H, W, 3)
        arr = arr / 255.0  # normalize to [0, 1]
        arr = arr.transpose(2, 0, 1)  # (3, H, W)
        return torch.from_numpy(arr)

    def _load_labels(
        self,
        pair: dict[str, Any],
        y: int,
        x: int,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Load segmentation and damage masks for a patch.

        Returns:
            (seg_mask_pre, seg_mask_post, damage_mask) as LongTensors of shape (patch_size, patch_size)
        """
        ps = self.patch_size

        if self.use_target_png:
            # Try loading pre-computed target masks (train only)
            seg_pre, seg_post, damage = self._load_target_png(pair, y, x)
            if seg_pre is not None:
                return seg_pre, seg_post, damage

        # Rasterize from JSON polygons
        # Pre-disaster: segmentation only (no damage subtype)
        if pair.get("lbl_pre") is not None:
            buildings_pre = parse_label_json(pair["lbl_pre"])
            seg_full_pre = rasterize_buildings(buildings_pre, mode="segmentation")
        else:
            seg_full_pre = np.zeros((1024, 1024), dtype=np.int64)

        # Post-disaster: segmentation + damage
        buildings_post = parse_label_json(pair["lbl_post"])
        seg_full_post = rasterize_buildings(buildings_post, mode="segmentation")
        damage_full = rasterize_buildings(buildings_post, mode="damage")

        # Crop to patch
        seg_pre = torch.from_numpy(seg_full_pre[y:y + ps, x:x + ps].copy())
        seg_post = torch.from_numpy(seg_full_post[y:y + ps, x:x + ps].copy())
        damage = torch.from_numpy(damage_full[y:y + ps, x:x + ps].copy())

        return seg_pre, seg_post, damage

    def _load_target_png(
        self,
        pair: dict[str, Any],
        y: int,
        x: int,
    ) -> tuple[Optional[torch.Tensor], Optional[torch.Tensor], Optional[torch.Tensor]]:
        """Try loading pre-computed target mask PNGs.

        target masks encode:
          - pixel value 0 = background
          - pixel value 1 = no-damage (building)
          - pixel value 2 = minor-damage
          - pixel value 3 = major-damage
          - pixel value 4 = destroyed

        Pre-disaster targets: only segmentation (0=bg, 1=building)
        """
        ps = self.patch_size
        data_root = pair["img_pre"].parent.parent  # up from images/

        pre_stem = pair["img_pre"].stem  # e.g. "disaster_00000_pre_disaster"
        post_stem = pair["img_post"].stem

        pre_target = data_root / self.targets_dir / f"{pre_stem}_target.png"
        post_target = data_root / self.targets_dir / f"{post_stem}_target.png"

        if not pre_target.exists() or not post_target.exists():
            return None, None, None

        pre_arr = np.array(Image.open(pre_target), dtype=np.int64)
        post_arr = np.array(Image.open(post_target), dtype=np.int64)

        # Pre-disaster: convert to binary segmentation
        seg_pre = (pre_arr > 0).astype(np.int64)
        seg_pre = torch.from_numpy(seg_pre[y:y + ps, x:x + ps].copy())

        # Post-disaster: binary segmentation
        seg_post = (post_arr > 0).astype(np.int64)
        seg_post = torch.from_numpy(seg_post[y:y + ps, x:x + ps].copy())

        # Damage mask = post target as-is (already 0-4)
        damage = torch.from_numpy(post_arr[y:y + ps, x:x + ps].copy())

        return seg_pre, seg_post, damage

    def _apply_augmentation(
        self,
        pre: torch.Tensor,
        post: torch.Tensor,
        seg_pre: torch.Tensor,
        seg_post: torch.Tensor,
        damage: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Apply consistent random augmentation to both pre/post images and masks.

        IMPORTANT: The SAME spatial transform must be applied to both images
        and all masks to maintain alignment.
        """
        # Random horizontal flip
        if torch.rand(1).item() > 0.5:
            pre = torch.flip(pre, [2])
            post = torch.flip(post, [2])
            seg_pre = torch.flip(seg_pre, [1])
            seg_post = torch.flip(seg_post, [1])
            damage = torch.flip(damage, [1])

        # Random vertical flip
        if torch.rand(1).item() > 0.5:
            pre = torch.flip(pre, [1])
            post = torch.flip(post, [1])
            seg_pre = torch.flip(seg_pre, [0])
            seg_post = torch.flip(seg_post, [0])
            damage = torch.flip(damage, [0])

        # Random 90-degree rotation
        k = torch.randint(0, 4, (1,)).item()
        if k > 0:
            pre = torch.rot90(pre, k, [1, 2])
            post = torch.rot90(post, k, [1, 2])
            seg_pre = torch.rot90(seg_pre, k, [0, 1])
            seg_post = torch.rot90(seg_post, k, [0, 1])
            damage = torch.rot90(damage, k, [0, 1])

        return pre, post, seg_pre, seg_post, damage


def compute_class_distribution(
    tile_pairs: list[dict[str, Any]],
    max_tiles: int | None = None,
) -> dict[str, Any]:
    """Compute damage class distribution across tiles.

    Args:
        tile_pairs: List of tile pair dicts
        max_tiles: Maximum tiles to process (None for all)

    Returns:
        Dict with class counts, percentages, and suggested weights
    """
    class_counts = np.zeros(5, dtype=np.int64)
    n_tiles = min(len(tile_pairs), max_tiles) if max_tiles else len(tile_pairs)

    for i, pair in enumerate(tile_pairs[:n_tiles]):
        buildings = parse_label_json(pair["lbl_post"])
        damage_mask = rasterize_buildings(buildings, mode="damage")
        for cls in range(5):
            class_counts[cls] += (damage_mask == cls).sum()

    total = class_counts.sum()
    percentages = (class_counts / total * 100) if total > 0 else np.zeros(5)

    # Compute inverse frequency weights (normalized)
    nonzero = class_counts[class_counts > 0]
    if len(nonzero) > 0:
        inv_freq = total / (5 * class_counts + 1)  # +1 to avoid div by zero
        weights = inv_freq / inv_freq.max()  # normalize to [0, 1]
    else:
        weights = np.ones(5)

    class_names = ["background", "no-damage", "minor-damage", "major-damage", "destroyed"]
    return {
        "class_names": class_names,
        "counts": {name: int(c) for name, c in zip(class_names, class_counts)},
        "percentages": {name: round(float(p), 2) for name, p in zip(class_names, percentages)},
        "suggested_weights": {name: round(float(w), 4) for name, w in zip(class_names, weights)},
        "total_pixels": int(total),
        "tiles_processed": n_tiles,
    }
