from __future__ import annotations

import json
from typing import Any

from app.config import get_settings
from app.services.geospatial.aoi import aoi_bbox, point_in_bbox
from app.services.paths import resolve_project_path


def summarize_hdx_for_aoi(aoi: dict[str, Any] | None) -> dict[str, Any]:
    settings = get_settings()
    root = resolve_project_path(settings.hdx_local_root)
    healthsites_path = root / "lebanon_healthsites" / "lebanon_healthsites.geojson" if root else None
    if not healthsites_path or not healthsites_path.exists():
        return {
            "status": "missing",
            "source": "local-hdx-cache",
            "counts": {},
            "message": "Local HDX healthsites cache is not available.",
            "worldpop": _worldpop_status(),
        }

    bbox = aoi_bbox(aoi)
    payload = json.loads(healthsites_path.read_text(encoding="utf-8"))
    counts = {"healthsites": 0, "hospitals": 0, "clinics": 0, "pharmacies": 0}
    sample_features: list[dict[str, Any]] = []
    for feature in payload.get("features", []):
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        if geometry.get("type") == "Point":
            lon, lat = coordinates[:2]
        elif geometry.get("type") == "Polygon" and coordinates and coordinates[0]:
            ring = coordinates[0]
            lon = sum(point[0] for point in ring) / len(ring)
            lat = sum(point[1] for point in ring) / len(ring)
        else:
            continue
        if not point_in_bbox(float(lon), float(lat), bbox):
            continue
        props = feature.get("properties") or {}
        amenity = str(props.get("amenity") or props.get("healthcare") or "").lower()
        counts["healthsites"] += 1
        if "hospital" in amenity:
            counts["hospitals"] += 1
        if "clinic" in amenity or "doctor" in amenity:
            counts["clinics"] += 1
        if "pharmacy" in amenity:
            counts["pharmacies"] += 1
        if len(sample_features) < 20:
            sample_features.append(feature)
    return {
        "status": "ready",
        "source": "local-hdx-cache",
        "path": str(healthsites_path),
        "bbox": bbox,
        "counts": counts,
        "sample": {"type": "FeatureCollection", "features": sample_features},
        "worldpop": _worldpop_status(),
    }


def _worldpop_status() -> dict[str, Any]:
    settings = get_settings()
    path = resolve_project_path(settings.worldpop_index_path)
    if not path or not path.exists():
        return {"status": "missing", "message": "WorldPop index is not available."}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = payload.get("data", [])
        latest = next((item for item in records if str(item.get("popyear")) == "2020"), records[-1] if records else {})
        return {
            "status": "metadata-ready",
            "path": str(path),
            "records": len(records),
            "latest_year": latest.get("popyear"),
            "download_url": (latest.get("files") or [None])[0],
            "note": "Population raster metadata is indexed; download the GeoTIFF to enable raster exposure sampling.",
        }
    except Exception as exc:
        return {"status": "warning", "path": str(path), "message": str(exc)}
