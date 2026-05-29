from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app.services.xbd.preprocessing import VALID_DAMAGE_SUBTYPES, label_summary


@dataclass(frozen=True)
class XBDTilePair:
    tile_id: str
    split: str
    pre_image: Path
    post_image: Path
    pre_label: Path
    post_label: Path


def _normalize_root(root: Path | str | None) -> Path | None:
    if root is None:
        return None
    return Path(root).expanduser()


def _base_tile_id(name: str) -> str:
    return name.replace("_pre_disaster", "").replace("_post_disaster", "")


def _index_files(folder: Path, suffix: str) -> dict[str, Path]:
    if not folder.exists():
        return {}
    return {_base_tile_id(path.stem): path for path in folder.glob(f"*{suffix}") if path.is_file()}


def discover_tile_pairs(root: Path | str | None, split: str) -> tuple[list[XBDTilePair], dict[str, object]]:
    dataset_root = _normalize_root(root)
    if dataset_root is None:
        return [], {"split": split, "configured": False, "exists": False, "errors": ["Dataset root is not configured"]}

    images_dir = dataset_root / "images"
    labels_dir = dataset_root / "labels"
    errors: list[str] = []
    if not dataset_root.exists():
        errors.append(f"Dataset root does not exist: {dataset_root}")
    if not images_dir.exists():
        errors.append(f"Missing images directory: {images_dir}")
    if not labels_dir.exists():
        errors.append(f"Missing labels directory: {labels_dir}")

    pre_images = _index_files(images_dir, "_pre_disaster.png")
    post_images = _index_files(images_dir, "_post_disaster.png")
    pre_labels = _index_files(labels_dir, "_pre_disaster.json")
    post_labels = _index_files(labels_dir, "_post_disaster.json")
    tile_ids = sorted(set(pre_images) | set(post_images) | set(pre_labels) | set(post_labels))

    pairs: list[XBDTilePair] = []
    missing: list[dict[str, object]] = []
    for tile_id in tile_ids:
        missing_parts = [
            label
            for label, index in {
                "pre_image": pre_images,
                "post_image": post_images,
                "pre_label": pre_labels,
                "post_label": post_labels,
            }.items()
            if tile_id not in index
        ]
        if missing_parts:
            missing.append({"tile_id": tile_id, "missing": missing_parts})
            continue
        pairs.append(
            XBDTilePair(
                tile_id=tile_id,
                split=split,
                pre_image=pre_images[tile_id],
                post_image=post_images[tile_id],
                pre_label=pre_labels[tile_id],
                post_label=post_labels[tile_id],
            )
        )

    status = {
        "split": split,
        "configured": True,
        "exists": dataset_root.exists(),
        "root": str(dataset_root),
        "image_count": len(pre_images) + len(post_images),
        "label_count": len(pre_labels) + len(post_labels),
        "paired_tiles": len(pairs),
        "missing_pairs": len(missing),
        "missing_samples": missing[:20],
        "errors": errors,
    }
    return pairs, status


def validate_dataset_root(root: Path | str | None, split: str, sample_limit: int | None = 100) -> dict[str, object]:
    pairs, status = discover_tile_pairs(root, split)
    invalid_subtypes: dict[str, int] = {}
    unreadable_labels: list[dict[str, str]] = []
    sampled_pairs = pairs if sample_limit is None else pairs[:sample_limit]

    for pair in sampled_pairs:
        try:
            summary = label_summary(pair.post_label)
        except Exception as exc:
            unreadable_labels.append({"tile_id": pair.tile_id, "path": str(pair.post_label), "error": str(exc)})
            continue
        for subtype in summary["damage_counts"]:
            if subtype not in VALID_DAMAGE_SUBTYPES:
                invalid_subtypes[subtype] = invalid_subtypes.get(subtype, 0) + 1

    return {
        **status,
        "sampled_tiles": len(sampled_pairs),
        "invalid_subtypes": invalid_subtypes,
        "unreadable_labels": unreadable_labels[:20],
        "valid": bool(status["configured"]) and bool(status["exists"]) and not status["errors"] and not status["missing_pairs"] and not unreadable_labels,
    }


def build_manifest(pairs: Iterable[XBDTilePair], sample_limit: int | None = None) -> list[dict[str, object]]:
    selected_pairs = list(pairs if sample_limit is None else list(pairs)[:sample_limit])
    records: list[dict[str, object]] = []
    for pair in selected_pairs:
        post_summary = label_summary(pair.post_label)
        pre_summary = label_summary(pair.pre_label)
        records.append(
            {
                "tile_id": pair.tile_id,
                "split": pair.split,
                "disaster": post_summary.get("disaster") or pre_summary.get("disaster"),
                "disaster_type": post_summary.get("disaster_type") or pre_summary.get("disaster_type"),
                "sensor": post_summary.get("sensor") or pre_summary.get("sensor"),
                "gsd": post_summary.get("gsd") or pre_summary.get("gsd"),
                "width": post_summary.get("width") or pre_summary.get("width"),
                "height": post_summary.get("height") or pre_summary.get("height"),
                "building_count": post_summary["building_count"],
                "damage_counts": post_summary["damage_counts"],
                "pre_image": str(pair.pre_image),
                "post_image": str(pair.post_image),
                "pre_label": str(pair.pre_label),
                "post_label": str(pair.post_label),
            }
        )
    return records


def build_manifest_for_roots(roots: dict[str, Path | str | None], sample_limit: int | None = None) -> dict[str, object]:
    datasets: dict[str, object] = {}
    all_records: list[dict[str, object]] = []
    for split, root in roots.items():
        pairs, status = discover_tile_pairs(root, split)
        split_limit = None if sample_limit is None else max(0, sample_limit - len(all_records))
        records = [] if split_limit == 0 else build_manifest(pairs, split_limit)
        datasets[split] = {**status, "manifest_records": len(records)}
        all_records.extend(records)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(all_records),
        "datasets": datasets,
        "tiles": all_records,
    }


def write_manifest(manifest: dict[str, object], artifacts_dir: Path | str, filename: str = "xbd_manifest.json") -> Path:
    output_dir = Path(artifacts_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return output_path


def pair_to_dict(pair: XBDTilePair) -> dict[str, object]:
    data = asdict(pair)
    return {key: str(value) if isinstance(value, Path) else value for key, value in data.items()}
