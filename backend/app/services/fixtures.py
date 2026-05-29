import json
from pathlib import Path

from app.config import get_settings
from app.models.schemas import BuildingDamage
from app.services.geospatial.damage import classify_damage


def load_beirut_fixture() -> dict:
    settings = get_settings()
    fixture_path = Path(settings.demo_fixture_dir) / "assessment.json"
    if not fixture_path.exists():
        fixture_path = Path(__file__).resolve().parents[3] / "data" / "fixtures" / "beirut" / "assessment.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def load_demo_buildings() -> list[BuildingDamage]:
    fixture = load_beirut_fixture()
    buildings = []
    for row in fixture["buildings"]:
        buildings.append(
            BuildingDamage(
                building_id=row["building_id"],
                name=row["name"],
                geometry=row["geometry"],
                centroid=tuple(row["centroid"]),
                damage_score=row["damage_score"],
                damage_tier=classify_damage(row["damage_score"]),
                infrastructure_type=row["infrastructure_type"],
                population_estimate=row["population_estimate"],
                estimated_cost_usd=row["estimated_cost_usd"],
                confidence=row["confidence"],
            )
        )
    return buildings
