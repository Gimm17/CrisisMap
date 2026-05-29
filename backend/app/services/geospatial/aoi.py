from __future__ import annotations

import math
from typing import Any


DEFAULT_BEIRUT_AOI = {
    "type": "Polygon",
    "coordinates": [
        [
            [35.507, 33.895],
            [35.531, 33.895],
            [35.531, 33.909],
            [35.507, 33.909],
            [35.507, 33.895],
        ]
    ],
}


class AoiValidationError(ValueError):
    pass


def validate_polygon_aoi(aoi: dict[str, Any] | None, require: bool = False) -> dict[str, Any] | None:
    if aoi is None:
        if require:
            raise AoiValidationError("AOI polygon is required")
        return None
    if aoi.get("type") != "Polygon":
        raise AoiValidationError("AOI must be a GeoJSON Polygon")
    rings = aoi.get("coordinates")
    if not isinstance(rings, list) or not rings or not isinstance(rings[0], list):
        raise AoiValidationError("AOI polygon coordinates are invalid")
    ring = rings[0]
    if len(ring) < 4:
        raise AoiValidationError("AOI polygon needs at least three vertices")
    normalized = []
    for point in ring:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            raise AoiValidationError("AOI coordinate must be [longitude, latitude]")
        lon = float(point[0])
        lat = float(point[1])
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise AoiValidationError("AOI coordinate is outside valid lon/lat bounds")
        normalized.append([lon, lat])
    if normalized[0] != normalized[-1]:
        normalized.append(normalized[0])
    if polygon_area_km2({"type": "Polygon", "coordinates": [normalized]}) <= 0:
        raise AoiValidationError("AOI polygon area must be greater than zero")
    return {"type": "Polygon", "coordinates": [normalized]}


def aoi_bbox(aoi: dict[str, Any] | None) -> tuple[float, float, float, float]:
    polygon = aoi or DEFAULT_BEIRUT_AOI
    ring = polygon["coordinates"][0]
    lons = [float(point[0]) for point in ring]
    lats = [float(point[1]) for point in ring]
    return min(lons), min(lats), max(lons), max(lats)


def point_in_bbox(lon: float, lat: float, bbox: tuple[float, float, float, float]) -> bool:
    min_lon, min_lat, max_lon, max_lat = bbox
    return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat


def polygon_area_km2(aoi: dict[str, Any]) -> float:
    ring = aoi["coordinates"][0]
    if len(ring) < 4:
        return 0.0
    mean_lat = sum(float(point[1]) for point in ring) / len(ring)
    meters_per_lon = 111_320 * math.cos(math.radians(mean_lat))
    meters_per_lat = 110_540
    origin_lon, origin_lat = ring[0]
    points = [
        ((float(lon) - float(origin_lon)) * meters_per_lon, (float(lat) - float(origin_lat)) * meters_per_lat)
        for lon, lat in ring
    ]
    area = 0.0
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[(index + 1) % len(points)]
        area += (x1 * y2) - (x2 * y1)
    return round(abs(area) / 2 / 1_000_000, 4)


def aoi_metadata(aoi: dict[str, Any] | None) -> dict[str, Any]:
    polygon = validate_polygon_aoi(aoi or DEFAULT_BEIRUT_AOI)
    assert polygon is not None
    return {
        "bbox": aoi_bbox(polygon),
        "area_km2": polygon_area_km2(polygon),
        "vertices": max(0, len(polygon["coordinates"][0]) - 1),
    }
