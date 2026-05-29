from __future__ import annotations

import json
from typing import Any

from app.config import get_settings
from app.services.geospatial.aoi import aoi_bbox, point_in_bbox
from app.services.paths import resolve_project_path


def _load_local_overpass() -> dict[str, Any] | None:
    settings = get_settings()
    path = resolve_project_path(settings.osm_overpass_local_path)
    if not path or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_live_overpass(aoi: dict[str, Any] | None) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    settings = get_settings()
    try:
        import httpx

        query = build_overpass_query(aoi)
        with httpx.Client(timeout=45) as client:
            response = client.post(settings.overpass_url, data={"data": query})
            response.raise_for_status()
        payload = response.json()
        cache_dir = settings.artifacts_dir / "osm"
        cache_dir.mkdir(parents=True, exist_ok=True)
        min_lon, min_lat, max_lon, max_lat = aoi_bbox(aoi)
        cache_path = cache_dir / f"overpass_{min_lon:.4f}_{min_lat:.4f}_{max_lon:.4f}_{max_lat:.4f}.json"
        cache_path.write_text(json.dumps(payload), encoding="utf-8")
        return payload, {"source": "overpass-live", "path": str(cache_path)}
    except Exception as exc:
        return None, {"source": "overpass-live", "message": str(exc)}


def summarize_osm_for_aoi(aoi: dict[str, Any] | None, *, allow_live: bool = False) -> dict[str, Any]:
    payload = _load_local_overpass()
    source_meta = {
        "source": "local-overpass-cache",
        "path": str(resolve_project_path(get_settings().osm_overpass_local_path)),
    }
    if payload is None and allow_live:
        payload, source_meta = _load_live_overpass(aoi)
    if payload is None:
        return {
            "status": "missing",
            "source": source_meta["source"],
            "counts": {},
            "message": source_meta.get("message", "Local OSM Overpass cache is not available."),
        }

    bbox = aoi_bbox(aoi)
    counts = {
        "elements": 0,
        "buildings": 0,
        "roads": 0,
        "hospitals": 0,
        "utilities": 0,
        "water": 0,
        "power": 0,
    }
    for element in payload.get("elements", []):
        lat = element.get("lat")
        lon = element.get("lon")
        if lat is None or lon is None:
            bounds = element.get("bounds") or {}
            if bounds:
                lat = (bounds.get("minlat", 0) + bounds.get("maxlat", 0)) / 2
                lon = (bounds.get("minlon", 0) + bounds.get("maxlon", 0)) / 2
        if lat is None or lon is None or not point_in_bbox(float(lon), float(lat), bbox):
            continue
        tags = element.get("tags") or {}
        counts["elements"] += 1
        if "building" in tags:
            counts["buildings"] += 1
        if "highway" in tags:
            counts["roads"] += 1
        if tags.get("amenity") == "hospital" or tags.get("healthcare") == "hospital":
            counts["hospitals"] += 1
        if "power" in tags:
            counts["power"] += 1
            counts["utilities"] += 1
        if "waterway" in tags or "water" in tags or tags.get("man_made") == "water_works":
            counts["water"] += 1
            counts["utilities"] += 1
    return {
        "status": "ready",
        **source_meta,
        "bbox": bbox,
        "counts": counts,
    }


def build_overpass_query(aoi: dict[str, Any] | None) -> str:
    min_lon, min_lat, max_lon, max_lat = aoi_bbox(aoi)
    return f"""
[out:json][timeout:60];
(
  way["building"]({min_lat},{min_lon},{max_lat},{max_lon});
  way["highway"]({min_lat},{min_lon},{max_lat},{max_lon});
  node["amenity"="hospital"]({min_lat},{min_lon},{max_lat},{max_lon});
  way["amenity"="hospital"]({min_lat},{min_lon},{max_lat},{max_lon});
  node["power"]({min_lat},{min_lon},{max_lat},{max_lon});
  way["power"]({min_lat},{min_lon},{max_lat},{max_lon});
  node["man_made"="water_works"]({min_lat},{min_lon},{max_lat},{max_lon});
  way["man_made"="water_works"]({min_lat},{min_lon},{max_lat},{max_lon});
);
out body geom;
"""
