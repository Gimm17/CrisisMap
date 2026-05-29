from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.models.schemas import BuildingDamage
from app.services.geospatial.damage import classify_damage
from app.services.paths import resolve_project_path


PORT_CENTER = (35.518, 33.901)


def _damage_score(label: str) -> int:
    normalized = label.strip().lower()
    if "destroyed" in normalized:
        return 94
    if normalized == "damaged" or "damaged" in normalized and "possibly" not in normalized:
        return 72
    if "possibly" in normalized:
        return 46
    return 10


def _infrastructure_type(properties: dict[str, Any]) -> str:
    info = f"{properties.get('obj_type', '')} {properties.get('info', '')}".lower()
    if "hospital" in info or "institutional care" in info:
        return "Medical Facility"
    if "industrial" in info or "warehouse" in info:
        return "Industrial Storage"
    if "communication" in info or "station" in info or "terminal" in info:
        return "Utility Infrastructure"
    if "residential" in info:
        return "Residential"
    if "transport" in info or "port" in info:
        return "Logistics Hub"
    return "Government" if "public" in info else "Residential"


def _square_polygon(lon: float, lat: float, score: int) -> dict[str, Any]:
    half_size = 0.00008 + (score / 1000000)
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [lon - half_size, lat - half_size],
                [lon + half_size, lat - half_size],
                [lon + half_size, lat + half_size],
                [lon - half_size, lat + half_size],
                [lon - half_size, lat - half_size],
            ]
        ],
    }


def _population_estimate(lon: float, lat: float, infrastructure_type: str, score: int) -> int:
    distance = math.dist((lon, lat), PORT_CENTER)
    proximity_factor = max(0.4, 1.4 - (distance * 35))
    type_factor = {
        "Medical Facility": 18000,
        "Utility Infrastructure": 12000,
        "Industrial Storage": 7500,
        "Logistics Hub": 6000,
        "Residential": 1800,
        "Government": 2500,
    }.get(infrastructure_type, 1500)
    return int(type_factor * proximity_factor * max(0.35, score / 80))


def _cost_estimate(infrastructure_type: str, score: int) -> int:
    base = {
        "Medical Facility": 4_800_000,
        "Utility Infrastructure": 3_600_000,
        "Industrial Storage": 5_200_000,
        "Logistics Hub": 4_400_000,
        "Residential": 700_000,
        "Government": 1_200_000,
    }.get(infrastructure_type, 850_000)
    return int(base * (0.45 + score / 100))


def load_beirut_ground_truth_buildings(limit: int | None = None) -> tuple[list[BuildingDamage], dict[str, Any]]:
    settings = get_settings()
    ground_truth_path = resolve_project_path(settings.beirut_ground_truth_path) or Path(settings.beirut_ground_truth_path)
    if not ground_truth_path.exists():
        return [], {
            "source": "copernicus-emsr452",
            "status": "missing",
            "path": str(ground_truth_path),
            "message": "Copernicus EMSR452 ground-truth GeoJSON was not found.",
        }

    payload = json.loads(ground_truth_path.read_text(encoding="utf-8"))
    features = payload.get("features", [])
    selected_features = features[: limit or settings.beirut_max_buildings]
    buildings: list[BuildingDamage] = []
    for index, feature in enumerate(selected_features, start=1):
        geometry = feature.get("geometry", {})
        if geometry.get("type") != "Point":
            continue
        lon, lat = geometry.get("coordinates", [None, None])[:2]
        if lon is None or lat is None:
            continue
        properties = feature.get("properties", {})
        damage_score = _damage_score(str(properties.get("damage_gra", "")))
        infrastructure_type = _infrastructure_type(properties)
        building_id = f"BEY-GT-{index:04d}"
        name = properties.get("name")
        if not name or str(name).lower() == "unknown":
            name = f"{infrastructure_type} {index:04d}"
        buildings.append(
            BuildingDamage(
                building_id=building_id,
                name=str(name),
                geometry=_square_polygon(float(lon), float(lat), damage_score),
                centroid=(float(lat), float(lon)),
                damage_score=damage_score,
                damage_tier=classify_damage(damage_score),
                infrastructure_type=infrastructure_type,
                population_estimate=_population_estimate(float(lon), float(lat), infrastructure_type, damage_score),
                estimated_cost_usd=_cost_estimate(infrastructure_type, damage_score),
                confidence=0.9 if damage_score >= 70 else 0.78,
            )
        )

    metadata = {
        "source": "copernicus-emsr452",
        "status": "ready",
        "path": str(ground_truth_path),
        "raw_feature_count": len(features),
        "building_count": len(buildings),
        "method": "Copernicus EMSR452 building damage points converted to CrisisMap building polygons for Beirut V1 validation.",
    }
    return buildings, metadata
