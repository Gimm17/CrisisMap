from datetime import date, datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


GeoJSONGeometry = dict[str, Any]
GeoJSONFeatureCollection = dict[str, Any]


class AssessmentStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class DamageTier(str, Enum):
    intact = "intact"
    minor = "minor"
    moderate = "moderate"
    severe = "severe"
    destroyed = "destroyed"


class DataSourceStatus(BaseModel):
    osm_buildings: Literal["ready", "pending", "failed"] = "ready"
    before_imagery: Literal["ready", "pending", "failed"] = "ready"
    after_imagery: Literal["ready", "pending", "failed"] = "ready"
    humanitarian_layers: Literal["ready", "pending", "failed"] = "ready"
    ai_reasoning: Literal["ready", "pending", "failed"] = "pending"


class AssessmentCreate(BaseModel):
    name: str = "Beirut Port Assessment"
    mode: Literal["demo", "live"] = "demo"
    location_name: str = "Beirut Port, Lebanon"
    aoi_geojson: GeoJSONGeometry | None = None
    event_date: date = Field(default=date(2020, 8, 4))
    pre_date_start: date = Field(default=date(2020, 7, 1))
    pre_date_end: date = Field(default=date(2020, 8, 3))
    post_date_start: date = Field(default=date(2020, 8, 5))
    post_date_end: date = Field(default=date(2020, 8, 15))
    model_profile: str = "damage"
    processing_priority: Literal["economy", "standard", "critical"] = "standard"
    tokenrouter_model: str | None = None

    @field_validator("post_date_start")
    @classmethod
    def post_after_event(cls, value: date, info: Any) -> date:
        event_date = info.data.get("event_date")
        if event_date and value <= event_date:
            raise ValueError("post_date_start must be after event_date")
        return value

    @field_validator("pre_date_end")
    @classmethod
    def pre_before_event(cls, value: date, info: Any) -> date:
        event_date = info.data.get("event_date")
        if event_date and value >= event_date:
            raise ValueError("pre_date_end must be before event_date")
        return value


class AssessmentSummary(BaseModel):
    buildings_assessed: int
    severe_or_destroyed: int
    critical_infrastructure_affected: int
    estimated_population_impact: int
    total_damage_score: float


class TokenRouterMetadata(BaseModel):
    provider: str = "heuristic-fallback"
    model: str = "local-heuristic"
    routing_mode: str = "offline"
    latency_ms: int = 0
    x_request_id: str | None = None


class BuildingDamage(BaseModel):
    building_id: str
    name: str
    geometry: GeoJSONGeometry
    centroid: tuple[float, float]
    damage_score: int
    damage_tier: DamageTier
    infrastructure_type: str
    population_estimate: int
    estimated_cost_usd: int
    confidence: float = Field(ge=0, le=1)
    priority_rank: int | None = None
    inference_method: str = "unknown"
    model_version: str | None = None
    validation_label: str | None = None
    validation_match: bool | None = None
    evidence: dict[str, Any] | None = None


class PriorityBuilding(BaseModel):
    rank: int
    building_id: str
    name: str
    infrastructure_type: str
    damage_score: int
    priority_score: float
    status: str
    reasoning: str
    affected_population: int
    estimated_cost_usd: int
    repair_timeline_days: int
    required_specialists: list[str]
    dependencies: list[str]
    confidence: float


class PhasedPlanItem(BaseModel):
    phase: str
    label: str
    actions: list[str]


class AssessmentReport(BaseModel):
    donor_summary: str
    damage_overview: str
    priority_buildings: list[PriorityBuilding]
    phased_plan: list[PhasedPlanItem]
    engineering_notes: str
    tokenrouter: TokenRouterMetadata


class AssessmentDetail(BaseModel):
    assessment_id: str = Field(default_factory=lambda: f"ASM-{uuid4().hex[:6].upper()}")
    name: str
    mode: Literal["demo", "live"]
    location_name: str
    status: AssessmentStatus
    progress: int = Field(ge=0, le=100)
    created_at: datetime
    completed_at: datetime | None = None
    runtime_seconds: int | None = None
    source_status: DataSourceStatus
    summary: AssessmentSummary | None = None
    tokenrouter: TokenRouterMetadata | None = None
    pipeline: dict[str, Any] | None = None
    error: str | None = None


class AnalysisSettings(BaseModel):
    model_profile: str = "damage"
    tokenrouter_model: str = "anthropic/claude-sonnet-4.6"
    confidence_threshold: int = Field(default=85, ge=50, le=99)
    processing_priority: Literal["economy", "standard", "critical"] = "standard"
    raw_imagery_retention_days: int = 90
    scrub_metadata_on_export: bool = False
    auto_publish_destroyed_tags: bool = True
