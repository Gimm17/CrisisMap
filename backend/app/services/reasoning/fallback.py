from app.models.schemas import AssessmentReport, BuildingDamage, PhasedPlanItem, PriorityBuilding, TokenRouterMetadata
from app.services.geospatial.damage import priority_weight


SPECIALISTS = {
    "Medical Facility": ["Structural Engineers", "Medical Gas Techs", "Telecom Specialists"],
    "Industrial Storage": ["Structural Engineers", "Heavy Equipment Operators", "Fire Safety Inspectors"],
    "Utility Infrastructure": ["Electrical Engineers", "Grid Technicians", "Safety Inspectors"],
    "Logistics Hub": ["Civil Engineers", "Debris Clearance Crews", "Transport Coordinators"],
    "Water System": ["Mechanical Engineers", "Pump Technicians", "Water Quality Specialists"],
    "Residential": ["Structural Engineers", "Shelter Coordinators", "Public Health Officers"],
}


def build_fallback_report(buildings: list[BuildingDamage], metadata: TokenRouterMetadata | None = None) -> AssessmentReport:
    ranked = sorted(buildings, key=priority_weight, reverse=True)
    priority_buildings: list[PriorityBuilding] = []
    for rank, building in enumerate(ranked[:5], start=1):
        building.priority_rank = rank
        score = priority_weight(building)
        status = _status_from_score(building.damage_score)
        dependencies = ["Debris clearance for safe access", "Temporary power stabilization"]
        if building.infrastructure_type == "Medical Facility":
            dependencies.append("Mobile care unit coverage before structural entry")
        if building.infrastructure_type == "Water System":
            dependencies.append("Water quality testing before service restoration")
        priority_buildings.append(
            PriorityBuilding(
                rank=rank,
                building_id=building.building_id,
                name=building.name,
                infrastructure_type=building.infrastructure_type,
                damage_score=building.damage_score,
                priority_score=score,
                status=status,
                reasoning=(
                    f"{building.name} is prioritized because it combines {building.damage_score}/100 damage, "
                    f"{building.infrastructure_type.lower()} function, and an estimated affected population of "
                    f"{building.population_estimate:,}."
                ),
                affected_population=building.population_estimate,
                estimated_cost_usd=building.estimated_cost_usd,
                repair_timeline_days=14 if building.damage_score >= 81 else 21 if building.damage_score >= 61 else 30,
                required_specialists=SPECIALISTS.get(building.infrastructure_type, ["Structural Engineers"]),
                dependencies=dependencies,
                confidence=building.confidence,
            )
        )
    return AssessmentReport(
        donor_summary=(
            "The Beirut Port assessment indicates severe structural damage across critical logistics, "
            "medical, and utility infrastructure. Immediate funding should prioritize life-sustaining "
            "systems and access corridors before broad reconstruction."
        ),
        damage_overview=(
            "The highest-risk assets cluster around port operations, medical care, power distribution, "
            "and dense residential blocks. Severe and destroyed categories require urgent field validation."
        ),
        priority_buildings=priority_buildings,
        phased_plan=[
            PhasedPlanItem(
                phase="0-72 Hours",
                label="Immediate Stabilization",
                actions=[
                    "Deploy rapid structural assessment teams to top-ranked assets.",
                    "Clear primary access corridors for emergency and logistics vehicles.",
                    "Set temporary medical and water distribution coverage for affected population clusters.",
                ],
            ),
            PhasedPlanItem(
                phase="1-2 Weeks",
                label="Early Recovery",
                actions=[
                    "Restore temporary power to medical and water infrastructure nodes.",
                    "Begin shoring of severe assets with high cascade effects.",
                    "Publish verified GeoJSON layers for partner coordination.",
                ],
            ),
            PhasedPlanItem(
                phase="1-3 Months",
                label="Infrastructure Restoration",
                actions=[
                    "Rebuild destroyed logistics and utility assets in dependency order.",
                    "Transition temporary services into permanent repairs.",
                    "Use updated imagery to validate reconstruction progress.",
                ],
            ),
        ],
        engineering_notes=(
            "Fallback reasoning was generated locally from deterministic damage scores and infrastructure weights. "
            "TokenRouter reasoning should be enabled for production-grade narrative review."
        ),
        tokenrouter=metadata or TokenRouterMetadata(),
    )


def _status_from_score(score: int) -> str:
    if score >= 81:
        return "Critical"
    if score >= 61:
        return "Severe"
    if score >= 41:
        return "Moderate"
    if score >= 21:
        return "Minor"
    return "Intact"
