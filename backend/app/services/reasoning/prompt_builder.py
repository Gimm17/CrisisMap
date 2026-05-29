from app.models.schemas import BuildingDamage


def build_reasoning_messages(buildings: list[BuildingDamage], humanitarian_layers: dict) -> list[dict[str, str]]:
    compact_buildings = [
        {
            "building_id": building.building_id,
            "name": building.name,
            "type": building.infrastructure_type,
            "damage_score": building.damage_score,
            "population_estimate": building.population_estimate,
            "estimated_cost_usd": building.estimated_cost_usd,
            "confidence": building.confidence,
        }
        for building in buildings
        if building.damage_score >= 40
    ]
    system = (
        "You are CrisisMap, a humanitarian infrastructure recovery advisor. "
        "Return only valid JSON matching the requested schema. Do not include markdown."
    )
    user = {
        "task": "Rank damaged infrastructure by humanitarian urgency and generate a phased reconstruction plan.",
        "humanitarian_layers": humanitarian_layers,
        "buildings": compact_buildings,
        "output_schema": {
            "donor_summary": "string",
            "damage_overview": "string",
            "priority_buildings": [
                {
                    "rank": "integer",
                    "building_id": "string",
                    "name": "string",
                    "infrastructure_type": "string",
                    "damage_score": "integer",
                    "priority_score": "number",
                    "status": "string",
                    "reasoning": "string",
                    "affected_population": "integer",
                    "estimated_cost_usd": "integer",
                    "repair_timeline_days": "integer",
                    "required_specialists": ["string"],
                    "dependencies": ["string"],
                    "confidence": "number between 0 and 1"
                }
            ],
            "phased_plan": [{"phase": "string", "label": "string", "actions": ["string"]}],
            "engineering_notes": "string"
        },
    }
    return [{"role": "system", "content": system}, {"role": "user", "content": str(user)}]
