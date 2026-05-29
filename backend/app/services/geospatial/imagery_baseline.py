from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.models.schemas import BuildingDamage
from app.services.geospatial.aoi import aoi_bbox
from app.services.geospatial.damage import classify_damage
from app.services.geospatial.ml_inference import ml_model_status, predict_building_damage
from app.services.paths import resolve_project_path


def _damage_score_from_change(change: float, area_m2: float) -> int:
    area_factor = min(12, area_m2 / 900)
    score = int(round((change * 190) + area_factor))
    return max(0, min(100, score))


def _infrastructure_type(area_m2: float, index: int) -> str:
    if area_m2 > 4500:
        return "Industrial Storage"
    if index % 41 == 0:
        return "Medical Facility"
    if index % 23 == 0:
        return "Utility Infrastructure"
    if index % 17 == 0:
        return "Logistics Hub"
    return "Residential"


def _population_estimate(infrastructure_type: str, damage_score: int, area_m2: float) -> int:
    base = {
        "Medical Facility": 18_000,
        "Utility Infrastructure": 11_000,
        "Industrial Storage": 6_000,
        "Logistics Hub": 5_500,
        "Residential": 900,
    }.get(infrastructure_type, 800)
    return int(base * max(0.35, damage_score / 80) + min(4000, area_m2 / 6))


def _cost_estimate(infrastructure_type: str, damage_score: int, area_m2: float) -> int:
    base = {
        "Medical Facility": 4_500_000,
        "Utility Infrastructure": 3_000_000,
        "Industrial Storage": 4_800_000,
        "Logistics Hub": 3_400_000,
        "Residential": 450_000,
    }.get(infrastructure_type, 500_000)
    return int(base * (0.25 + damage_score / 100) + area_m2 * 280)


def _read_footprints(aoi: dict[str, Any], limit: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    import shapefile
    from pyproj import Transformer
    from shapely.geometry import Polygon, box, mapping
    from shapely.ops import transform

    settings = get_settings()
    path = resolve_project_path(settings.beirut_footprints_path)
    if not path or not path.exists():
        return [], {"status": "missing", "path": str(path)}

    bbox = aoi_bbox(aoi)
    aoi_box = box(*bbox)
    transformer = Transformer.from_crs("EPSG:32636", "EPSG:4326", always_xy=True)
    reader = shapefile.Reader(str(path))
    footprints: list[dict[str, Any]] = []
    for index, shape_record in enumerate(reader.iterShapeRecords(), start=1):
        points = shape_record.shape.points
        if len(points) < 4:
            continue
        polygon_utm = Polygon(points)
        if not polygon_utm.is_valid or polygon_utm.area <= 0:
            continue
        polygon_wgs = transform(transformer.transform, polygon_utm)
        if not polygon_wgs.intersects(aoi_box):
            continue
        clipped = polygon_wgs.intersection(aoi_box)
        if clipped.is_empty or clipped.area <= 0:
            continue
        if clipped.geom_type == "MultiPolygon":
            clipped = max(clipped.geoms, key=lambda geom: geom.area)
        footprints.append(
            {
                "index": index,
                "geometry": mapping(clipped),
                "bbox": clipped.bounds,
                "centroid": (clipped.centroid.y, clipped.centroid.x),
                "area_m2": float(polygon_utm.area),
            }
        )
        if len(footprints) >= limit:
            break
    return footprints, {"status": "ready", "path": str(path), "raw_count": len(reader), "selected_count": len(footprints)}


def _mean_change(pre_path: Path, post_path: Path, bbox: tuple[float, float, float, float]) -> tuple[float, dict[str, Any]]:
    import numpy as np
    import rasterio
    from rasterio.windows import from_bounds

    with rasterio.open(pre_path) as pre_src, rasterio.open(post_path) as post_src:
        pre_window = from_bounds(*bbox, transform=pre_src.transform).round_offsets().round_lengths()
        post_window = from_bounds(*bbox, transform=post_src.transform).round_offsets().round_lengths()
        if pre_window.width <= 1 or pre_window.height <= 1 or post_window.width <= 1 or post_window.height <= 1:
            return 0.0, {"status": "empty-window"}
        pre = pre_src.read(indexes=[1, 2, 3], window=pre_window, out_shape=(3, 64, 64), boundless=True, fill_value=0)
        post = post_src.read(indexes=[1, 2, 3], window=post_window, out_shape=(3, 64, 64), boundless=True, fill_value=0)
    pre = pre.astype("float32")
    post = post.astype("float32")
    scale = max(float(pre.max(initial=1)), float(post.max(initial=1)), 255.0)
    diff = np.abs(pre - post) / scale
    usable = (pre.sum(axis=0) > 0) & (post.sum(axis=0) > 0)
    if not usable.any():
        return 0.0, {"status": "nodata"}
    return float(diff[:, usable].mean()), {"status": "ready"}


def _save_chip_artifact(assessment_id: str, building_id: str, bbox: tuple[float, float, float, float]) -> dict[str, str] | None:
    try:
        import numpy as np
        import rasterio
        from PIL import Image
        from rasterio.windows import from_bounds

        settings = get_settings()
        pre_path = resolve_project_path(settings.beirut_maxar_pre_path)
        post_path = resolve_project_path(settings.beirut_maxar_post_path)
        if not pre_path or not post_path:
            return None
        output_dir = settings.artifacts_dir / "chips" / assessment_id
        output_dir.mkdir(parents=True, exist_ok=True)
        outputs: dict[str, str] = {}
        for label, path in {"pre": pre_path, "post": post_path}.items():
            with rasterio.open(path) as src:
                window = from_bounds(*bbox, transform=src.transform).round_offsets().round_lengths()
                data = src.read(indexes=[1, 2, 3], window=window, out_shape=(3, 128, 128), boundless=True, fill_value=0)
            image = np.moveaxis(data, 0, -1)
            if image.max(initial=0) > 255:
                image = (image / max(image.max(), 1) * 255).astype("uint8")
            else:
                image = image.astype("uint8")
            output_path = output_dir / f"{building_id}_{label}.png"
            Image.fromarray(image).save(output_path)
            outputs[label] = str(output_path)
        return outputs
    except Exception:
        return None


def _load_validation_points() -> list[dict[str, Any]]:
    settings = get_settings()
    path = resolve_project_path(settings.beirut_ground_truth_path)
    if not path or not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("features", [])


def _validation_label_for_bbox(bbox: tuple[float, float, float, float], points: list[dict[str, Any]]) -> str | None:
    min_lon, min_lat, max_lon, max_lat = bbox
    pad = 0.00025
    for feature in points:
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "Point":
            continue
        lon, lat = geometry.get("coordinates", [None, None])[:2]
        if lon is None or lat is None:
            continue
        if min_lon - pad <= lon <= max_lon + pad and min_lat - pad <= lat <= max_lat + pad:
            return str((feature.get("properties") or {}).get("damage_gra") or "")
    return None


def _ground_truth_to_tier(label: str | None) -> str | None:
    normalized = (label or "").strip().lower()
    if normalized == "destroyed":
        return "destroyed"
    if normalized == "damaged":
        return "severe"
    if normalized == "possibly damaged":
        return "minor"
    return None


def _validation_metrics(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    labels = ["minor", "moderate", "severe", "destroyed"]
    matrix = {truth: {predicted: 0 for predicted in labels} for truth in labels}
    for truth, predicted in pairs:
        if truth not in matrix:
            continue
        predicted_key = predicted if predicted in labels else "minor"
        matrix[truth][predicted_key] += 1

    per_class: dict[str, Any] = {}
    f1_values: list[float] = []
    correct = 0
    for label in labels:
        tp = matrix[label][label]
        fp = sum(matrix[truth][label] for truth in labels if truth != label)
        fn = sum(matrix[label][predicted] for predicted in labels if predicted != label)
        correct += tp
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        f1_values.append(f1)
        per_class[label] = {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "support": sum(matrix[label].values()),
        }

    total = len(pairs)
    return {
        "matched_buildings": total,
        "accuracy": round(correct / total, 3) if total else 0.0,
        "macro_f1": round(sum(f1_values) / len(f1_values), 3) if f1_values else 0.0,
        "per_class": per_class,
        "confusion_matrix": matrix,
        "label_mapping": {
            "Possibly damaged": "minor",
            "Damaged": "severe",
            "Destroyed": "destroyed",
        },
    }


def run_beirut_imagery_baseline(aoi: dict[str, Any], assessment_id: str, limit: int | None = None) -> tuple[list[BuildingDamage], dict[str, Any]]:
    settings = get_settings()
    pre_path = resolve_project_path(settings.beirut_maxar_pre_path)
    post_path = resolve_project_path(settings.beirut_maxar_post_path)
    max_buildings = limit or min(settings.beirut_max_buildings, 180)
    if not pre_path or not pre_path.exists() or not post_path or not post_path.exists():
        return [], {"method": "imagery-baseline", "status": "missing-imagery"}

    try:
        footprints, footprint_meta = _read_footprints(aoi, max_buildings)
    except Exception as exc:
        return [], {"method": "imagery-baseline", "status": "failed", "error": str(exc)}
    if not footprints:
        return [], {"method": "imagery-baseline", "status": "no-footprints", "footprints": footprint_meta}

    validation_points = _load_validation_points()
    model_status = ml_model_status()
    buildings: list[BuildingDamage] = []
    validation_matches = 0
    validation_pairs: list[tuple[str, str]] = []
    chip_artifacts: dict[str, Any] = {}
    prediction_details: dict[str, Any] = {}
    method_counts = {"ml-inference": 0, "imagery-baseline": 0}
    for output_index, footprint in enumerate(footprints, start=1):
        bbox = tuple(float(value) for value in footprint["bbox"])
        change, change_meta = _mean_change(pre_path, post_path, bbox)
        baseline_score = _damage_score_from_change(change, footprint["area_m2"])
        damage_score = baseline_score
        confidence = 0.58 + min(0.34, change * 0.8)
        inference_method = "imagery-baseline"
        model_version: str | None = None
        predicted_class: str | None = None
        probabilities: dict[str, float] | None = None
        ml_prediction = None
        if model_status.get("status") == "ready":
            try:
                ml_prediction = predict_building_damage(pre_path, post_path, bbox, baseline_score=baseline_score)
            except Exception as exc:
                prediction_details[f"BEY-IMG-{output_index:04d}"] = {"ml_error": str(exc)}
        if ml_prediction:
            damage_score = ml_prediction.damage_score
            confidence = ml_prediction.confidence
            inference_method = "ml-inference"
            model_version = ml_prediction.model_version
            predicted_class = ml_prediction.predicted_class
            probabilities = ml_prediction.probabilities
        method_counts[inference_method] += 1
        validation_label = _validation_label_for_bbox(bbox, validation_points)
        validation_tier = _ground_truth_to_tier(validation_label)
        predicted_tier = classify_damage(damage_score).value
        validation_match: bool | None = None
        if validation_label:
            validation_matches += 1
        if validation_tier:
            validation_match = validation_tier == predicted_tier
            validation_pairs.append((validation_tier, predicted_tier))
        infrastructure_type = _infrastructure_type(footprint["area_m2"], output_index)
        building_id = f"BEY-IMG-{output_index:04d}"
        chips = _save_chip_artifact(assessment_id, building_id, bbox)
        if chips:
            chip_artifacts[building_id] = chips
        if change_meta["status"] != "ready":
            confidence = 0.42
        prediction_details.setdefault(
            building_id,
            {
                "inference_method": inference_method,
                "model_version": model_version,
                "predicted_class": predicted_class,
                "probabilities": probabilities,
                "baseline_change_score": round(change, 6),
                "baseline_damage_score": baseline_score,
                "final_damage_score": damage_score,
                "validation_label": validation_label,
                "validation_tier": validation_tier,
                "validation_match": validation_match,
            },
        )
        buildings.append(
            BuildingDamage(
                building_id=building_id,
                name=f"{infrastructure_type} {output_index:04d}",
                geometry=footprint["geometry"],
                centroid=tuple(footprint["centroid"]),
                damage_score=damage_score,
                damage_tier=classify_damage(damage_score),
                infrastructure_type=infrastructure_type,
                population_estimate=_population_estimate(infrastructure_type, damage_score, footprint["area_m2"]),
                estimated_cost_usd=_cost_estimate(infrastructure_type, damage_score, footprint["area_m2"]),
                confidence=round(min(0.95, max(0.35, confidence)), 3),
                inference_method=inference_method,
                model_version=model_version,
                validation_label=validation_label,
                validation_match=validation_match,
                evidence={
                    "chip_available": bool(chips),
                    "predicted_class": predicted_class,
                    "baseline_damage_score": baseline_score,
                    "baseline_change_score": round(change, 6),
                },
            )
        )

    severe = len([building for building in buildings if building.damage_score >= 61])
    active_method = "ml-inference" if method_counts["ml-inference"] else "imagery-baseline"
    validation_summary = _validation_metrics(validation_pairs)
    metadata = {
        "method": active_method,
        "status": "ready",
        "pre_imagery": str(pre_path),
        "post_imagery": str(post_path),
        "footprints": footprint_meta,
        "model": model_status,
        "method_counts": method_counts,
        "prediction_details": prediction_details,
        "chip_artifacts": chip_artifacts,
        "validation": {
            "ground_truth_points": len(validation_points),
            "matched_buildings": validation_matches,
            "predicted_severe_or_destroyed": severe,
            "metrics": validation_summary,
            "note": "Validation is nearest-point overlap against Copernicus EMSR452; it is not used as training data.",
        },
        "limitations": [
            "SiamUnet inference is used only when PyTorch and checkpoint loading are available; otherwise deterministic image-change scoring is used.",
            "The public checkpoint was trained on xBD-style disaster tiles and is blended with image-change scoring for Beirut domain transfer.",
            "Field validation is still required before operational intervention.",
        ],
    }
    return buildings, metadata
