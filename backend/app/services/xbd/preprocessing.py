from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


VALID_DAMAGE_SUBTYPES = {
    "no-damage",
    "minor-damage",
    "major-damage",
    "destroyed",
    "un-classified",
}

SUBTYPE_TO_CLASS = {
    "no-damage": 1,
    "minor-damage": 2,
    "major-damage": 3,
    "destroyed": 4,
    "un-classified": 5,
}

SUBTYPE_TO_SCORE = {
    "no-damage": 8,
    "minor-damage": 28,
    "major-damage": 68,
    "destroyed": 94,
    "un-classified": 0,
}

_POINT_PATTERN = re.compile(r"(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)")


@dataclass(frozen=True)
class XBDPolygon:
    uid: str
    subtype: str
    damage_class: int
    xy_wkt: str
    lng_lat_wkt: str | None
    bbox_xy: tuple[float, float, float, float]
    area_px: float


def load_label_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_polygon_wkt(wkt: str) -> list[tuple[float, float]]:
    points = [(float(x), float(y)) for x, y in _POINT_PATTERN.findall(wkt)]
    if len(points) < 3:
        raise ValueError("Polygon WKT must contain at least three points")
    return points


def polygon_bbox(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def polygon_area(points: list[tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    total = 0.0
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[(index + 1) % len(points)]
        total += (x1 * y2) - (x2 * y1)
    return abs(total) / 2


def extract_xbd_polygons(label_path: Path) -> list[XBDPolygon]:
    payload = load_label_json(label_path)
    features = payload.get("features", {})
    xy_features = features.get("xy", [])
    lng_lat_features = features.get("lng_lat", [])
    lng_lat_by_uid = {
        feature.get("properties", {}).get("uid"): feature.get("wkt")
        for feature in lng_lat_features
        if feature.get("properties", {}).get("uid")
    }

    polygons: list[XBDPolygon] = []
    for feature in xy_features:
        properties = feature.get("properties", {})
        subtype = properties.get("subtype", "un-classified")
        if subtype not in VALID_DAMAGE_SUBTYPES:
            subtype = "un-classified"
        uid = properties.get("uid") or f"{label_path.stem}-{len(polygons) + 1}"
        xy_wkt = feature.get("wkt", "")
        points = parse_polygon_wkt(xy_wkt)
        polygons.append(
            XBDPolygon(
                uid=uid,
                subtype=subtype,
                damage_class=SUBTYPE_TO_CLASS[subtype],
                xy_wkt=xy_wkt,
                lng_lat_wkt=lng_lat_by_uid.get(uid),
                bbox_xy=polygon_bbox(points),
                area_px=polygon_area(points),
            )
        )
    return polygons


def label_summary(label_path: Path) -> dict[str, Any]:
    payload = load_label_json(label_path)
    metadata = payload.get("metadata", {})
    polygons = extract_xbd_polygons(label_path)
    damage_counts: dict[str, int] = {subtype: 0 for subtype in sorted(VALID_DAMAGE_SUBTYPES)}
    for polygon in polygons:
        damage_counts[polygon.subtype] = damage_counts.get(polygon.subtype, 0) + 1
    return {
        "img_name": metadata.get("img_name"),
        "disaster": metadata.get("disaster"),
        "disaster_type": metadata.get("disaster_type"),
        "sensor": metadata.get("sensor"),
        "gsd": metadata.get("gsd"),
        "capture_date": metadata.get("capture_date"),
        "width": metadata.get("width"),
        "height": metadata.get("height"),
        "building_count": len(polygons),
        "damage_counts": damage_counts,
    }

