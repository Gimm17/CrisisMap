from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from app.services.xbd.preprocessing import SUBTYPE_TO_SCORE, XBDPolygon, extract_xbd_polygons
from app.services.xbd.registry import XBDTilePair


@dataclass(frozen=True)
class BuildingDamagePrediction:
    tile_id: str
    building_uid: str
    bbox_xy: tuple[int, int, int, int]
    change_score: float
    damage_score: int
    predicted_subtype: str
    ground_truth_subtype: str
    confidence: float


def _safe_bbox(bbox: tuple[float, float, float, float], size: tuple[int, int], padding: int = 8) -> tuple[int, int, int, int] | None:
    width, height = size
    left = max(0, int(bbox[0]) - padding)
    top = max(0, int(bbox[1]) - padding)
    right = min(width, int(bbox[2]) + padding)
    bottom = min(height, int(bbox[3]) + padding)
    if right <= left or bottom <= top:
        return None
    return left, top, right, bottom


def _mean_abs_change(pre_image: Image.Image, post_image: Image.Image, bbox: tuple[int, int, int, int]) -> float:
    pre_crop = pre_image.crop(bbox).convert("RGB")
    post_crop = post_image.crop(bbox).convert("RGB")
    diff = ImageChops.difference(pre_crop, post_crop)
    return float(sum(ImageStat.Stat(diff).mean) / 3)


def _score_to_subtype(score: int) -> str:
    if score >= 82:
        return "destroyed"
    if score >= 58:
        return "major-damage"
    if score >= 28:
        return "minor-damage"
    return "no-damage"


def _change_to_damage_score(change_score: float, polygon: XBDPolygon) -> int:
    area_factor = min(14, polygon.area_px / 9000)
    score = int(round((change_score * 2.6) + area_factor))
    return max(0, min(100, score))


class ImageChangeDamageModel:
    """Lightweight local baseline for pre/post xBD imagery.

    This is intentionally simple and deterministic. It proves the ingestion,
    crop, inference, and building-level output path before heavier Torch/rasterio
    models are wired into the production pipeline.
    """

    def predict_pair(self, pair: XBDTilePair, max_buildings: int = 100) -> list[BuildingDamagePrediction]:
        polygons = extract_xbd_polygons(pair.post_label)[:max_buildings]
        predictions: list[BuildingDamagePrediction] = []
        with Image.open(pair.pre_image) as pre_image_raw, Image.open(pair.post_image) as post_image_raw:
            pre_image = pre_image_raw.convert("RGB")
            post_image = post_image_raw.convert("RGB")
            if pre_image.size != post_image.size:
                post_image = post_image.resize(pre_image.size)

            for polygon in polygons:
                bbox = _safe_bbox(polygon.bbox_xy, pre_image.size)
                if bbox is None:
                    continue
                change_score = _mean_abs_change(pre_image, post_image, bbox)
                damage_score = _change_to_damage_score(change_score, polygon)
                predicted_subtype = _score_to_subtype(damage_score)
                label_score = SUBTYPE_TO_SCORE.get(polygon.subtype, 0)
                confidence = max(0.35, min(0.98, 1 - abs(damage_score - label_score) / 130))
                predictions.append(
                    BuildingDamagePrediction(
                        tile_id=pair.tile_id,
                        building_uid=polygon.uid,
                        bbox_xy=bbox,
                        change_score=round(change_score, 2),
                        damage_score=damage_score,
                        predicted_subtype=predicted_subtype,
                        ground_truth_subtype=polygon.subtype,
                        confidence=round(confidence, 3),
                    )
                )
        return predictions


def summarize_predictions(predictions: list[BuildingDamagePrediction]) -> dict[str, object]:
    buckets = {"no-damage": 0, "minor-damage": 0, "major-damage": 0, "destroyed": 0}
    for prediction in predictions:
        buckets[prediction.predicted_subtype] = buckets.get(prediction.predicted_subtype, 0) + 1
    return {
        "building_count": len(predictions),
        "predicted_damage_counts": buckets,
        "mean_damage_score": round(sum(item.damage_score for item in predictions) / max(len(predictions), 1), 2),
        "mean_confidence": round(sum(item.confidence for item in predictions) / max(len(predictions), 1), 3),
    }


def load_pair_from_manifest_record(record: dict[str, object]) -> XBDTilePair:
    return XBDTilePair(
        tile_id=str(record["tile_id"]),
        split=str(record["split"]),
        pre_image=Path(str(record["pre_image"])),
        post_image=Path(str(record["post_image"])),
        pre_label=Path(str(record["pre_label"])),
        post_label=Path(str(record["post_label"])),
    )

