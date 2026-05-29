from app.models.schemas import BuildingDamage, DamageTier


def classify_damage(score: int) -> DamageTier:
    if score >= 81:
        return DamageTier.destroyed
    if score >= 61:
        return DamageTier.severe
    if score >= 41:
        return DamageTier.moderate
    if score >= 21:
        return DamageTier.minor
    return DamageTier.intact


def priority_weight(building: BuildingDamage) -> float:
    infra_multiplier = {
        "Medical Facility": 1.45,
        "Water System": 1.35,
        "Utility Infrastructure": 1.3,
        "Logistics Hub": 1.2,
        "Industrial Storage": 1.15,
        "Residential": 1.05,
    }.get(building.infrastructure_type, 1.0)
    population_factor = min(building.population_estimate / 10000, 5.0)
    cost_efficiency = max(0.55, 1 - (building.estimated_cost_usd / 25000000))
    return round((building.damage_score / 10) * infra_multiplier + population_factor + cost_efficiency, 2)


def building_to_feature(building: BuildingDamage) -> dict:
    return {
        "type": "Feature",
        "id": building.building_id,
        "geometry": building.geometry,
        "properties": {
            "building_id": building.building_id,
            "name": building.name,
            "damage_score": building.damage_score,
            "damage_tier": building.damage_tier.value,
            "infrastructure_type": building.infrastructure_type,
            "population_estimate": building.population_estimate,
            "estimated_cost_usd": building.estimated_cost_usd,
            "confidence": building.confidence,
            "priority_rank": building.priority_rank,
            "inference_method": building.inference_method,
            "model_version": building.model_version,
            "validation_label": building.validation_label,
            "validation_match": building.validation_match,
            "evidence": building.evidence,
        },
    }


def to_feature_collection(buildings: list[BuildingDamage]) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [building_to_feature(building) for building in buildings],
    }
