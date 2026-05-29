import type { Assessment, AssessmentReport, BuildingFeatureCollection, PriorityBuilding } from "./types";

export const demoAssessment: Assessment = {
  assessment_id: "ASM-DEMO",
  name: "Beirut Port Assessment",
  mode: "demo",
  location_name: "Beirut Port, Lebanon",
  status: "completed",
  progress: 100,
  created_at: "2026-05-18T08:00:00Z",
  completed_at: "2026-05-18T08:02:14Z",
  runtime_seconds: 134,
  summary: {
    buildings_assessed: 1420,
    severe_or_destroyed: 84,
    critical_infrastructure_affected: 12,
    estimated_population_impact: 155000,
    total_damage_score: 84.2
  },
  tokenrouter: {
    provider: "heuristic-fallback",
    model: "local-heuristic",
    routing_mode: "offline",
    latency_ms: 0
  }
};

export const demoPriorities: PriorityBuilding[] = [
  {
    rank: 1,
    building_id: "B-1001",
    name: "St. George Hospital",
    infrastructure_type: "Medical Facility",
    damage_score: 98,
    priority_score: 18.7,
    status: "Critical",
    reasoning:
      "St. George Hospital is a critical single point of failure for medical logistics. Loss of surgical capacity pushes surrounding clinics beyond capacity within 12 hours.",
    affected_population: 45000,
    estimated_cost_usd: 12400000,
    repair_timeline_days: 14,
    required_specialists: ["Structural Engineers", "Medical Gas Techs", "Telecom Specialists"],
    dependencies: ["Debris clearance required for Zone A access.", "Power grid stabilization to tertiary nodes."],
    confidence: 0.94
  },
  {
    rank: 2,
    building_id: "B-1002",
    name: "Port Silo Complex A",
    infrastructure_type: "Industrial Storage",
    damage_score: 89,
    priority_score: 14.9,
    status: "Severe",
    reasoning:
      "The silo complex blocks heavy machinery access and constrains port logistics recovery for food and shelter supply routes.",
    affected_population: 15000,
    estimated_cost_usd: 15200000,
    repair_timeline_days: 21,
    required_specialists: ["Structural Engineers", "Heavy Equipment Operators"],
    dependencies: ["Fire safety inspection", "Heavy debris clearance"],
    confidence: 0.91
  },
  {
    rank: 3,
    building_id: "B-1003",
    name: "Power Substation A",
    infrastructure_type: "Utility Infra",
    damage_score: 85,
    priority_score: 13.8,
    status: "Severe",
    reasoning:
      "Substation restoration unlocks temporary power for medical, water, and logistics assets across the assessment area.",
    affected_population: 32000,
    estimated_cost_usd: 4800000,
    repair_timeline_days: 14,
    required_specialists: ["Electrical Engineers", "Grid Technicians"],
    dependencies: ["Grid isolation", "Safety perimeter"],
    confidence: 0.89
  }
];

export const demoReport: AssessmentReport = {
  donor_summary:
    "The blast zone assessment indicates catastrophic structural failure across critical port infrastructure. Immediate funding should prioritize medical continuity, utility stabilization, and logistics access.",
  damage_overview:
    "CrisisMap assessed 1,420 structures in the Beirut Port AOI. Eighty-four structures fall into severe or destroyed categories, including 12 critical infrastructure assets.",
  priority_buildings: demoPriorities,
  phased_plan: [
    {
      phase: "0-72 Hours",
      label: "Immediate Stabilization",
      actions: ["Deploy USAR teams to Sectors A and B.", "Secure overhangs near main arteries.", "Establish emergency triage perimeters."]
    },
    {
      phase: "1-2 Weeks",
      label: "Early Recovery",
      actions: ["Clear primary road corridors.", "Restore temporary power to medical nodes.", "Begin shoring of severe assets."]
    },
    {
      phase: "1-3 Months",
      label: "Infrastructure Restoration",
      actions: ["Rebuild Port Silo foundation.", "Restore permanent utilities.", "Initiate long-term recovery grants."]
    }
  ],
  engineering_notes:
    "Damage assessments are derived from multi-source imagery and deterministic fixture scores. Field validation is required before physical intervention.",
  tokenrouter: demoAssessment.tokenrouter!
};

export const demoGeoJson: BuildingFeatureCollection = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      id: "B-1001",
      geometry: { type: "Polygon", coordinates: [[[35.5174, 33.9012], [35.5192, 33.9012], [35.5192, 33.9026], [35.5174, 33.9026], [35.5174, 33.9012]]] },
      properties: {
        building_id: "B-1001",
        name: "St. George Hospital",
        damage_score: 98,
        damage_tier: "destroyed",
        infrastructure_type: "Medical Facility",
        population_estimate: 45000,
        estimated_cost_usd: 12400000,
        confidence: 0.94,
        priority_rank: 1
      }
    },
    {
      type: "Feature",
      id: "B-1002",
      geometry: { type: "Polygon", coordinates: [[[35.5131, 33.902], [35.5155, 33.902], [35.5155, 33.9037], [35.5131, 33.9037], [35.5131, 33.902]]] },
      properties: {
        building_id: "B-1002",
        name: "Port Silo Complex A",
        damage_score: 89,
        damage_tier: "destroyed",
        infrastructure_type: "Industrial Storage",
        population_estimate: 15000,
        estimated_cost_usd: 15200000,
        confidence: 0.91,
        priority_rank: 2
      }
    },
    {
      type: "Feature",
      id: "B-1003",
      geometry: { type: "Polygon", coordinates: [[[35.5217, 33.8985], [35.5237, 33.8985], [35.5237, 33.9], [35.5217, 33.9], [35.5217, 33.8985]]] },
      properties: {
        building_id: "B-1003",
        name: "Power Substation A",
        damage_score: 85,
        damage_tier: "destroyed",
        infrastructure_type: "Utility Infrastructure",
        population_estimate: 32000,
        estimated_cost_usd: 4800000,
        confidence: 0.89,
        priority_rank: 3
      }
    }
  ]
};
