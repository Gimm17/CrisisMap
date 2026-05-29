from __future__ import annotations

from datetime import datetime, timezone

from app.config import get_settings
from app.core.store import store
from app.models.schemas import (
    AssessmentCreate,
    AssessmentDetail,
    AssessmentStatus,
    AssessmentSummary,
    DataSourceStatus,
)
from app.core.analysis_settings import get_analysis_settings_state
from app.services.data_sources.readiness import data_source_status
from app.services.fixtures import load_beirut_fixture, load_demo_buildings
from app.services.geospatial.aoi import DEFAULT_BEIRUT_AOI, aoi_metadata, validate_polygon_aoi
from app.services.geospatial.beirut_real import load_beirut_ground_truth_buildings
from app.services.geospatial.damage import to_feature_collection
from app.services.geospatial.imagery_baseline import run_beirut_imagery_baseline
from app.services.reasoning.tokenrouter import TokenRouterReasoner
from app.services.xbd.registry import validate_dataset_root


def summarize(buildings) -> AssessmentSummary:
    severe_or_destroyed = len([b for b in buildings if b.damage_score >= 61])
    critical_infra = len(
        [
            b
            for b in buildings
            if b.damage_score >= 61
            and b.infrastructure_type in {"Medical Facility", "Water System", "Utility Infrastructure", "Logistics Hub"}
        ]
    )
    population = sum(building.population_estimate for building in buildings if building.damage_score >= 41)
    if population == 0:
        population = sum(building.population_estimate for building in buildings)
    return AssessmentSummary(
        buildings_assessed=len(buildings),
        severe_or_destroyed=severe_or_destroyed,
        critical_infrastructure_affected=critical_infra,
        estimated_population_impact=population,
        total_damage_score=round(sum(building.damage_score for building in buildings) / max(len(buildings), 1), 2),
    )


def load_assessment_buildings() -> tuple[list, dict]:
    buildings, metadata = load_beirut_ground_truth_buildings()
    if buildings:
        return buildings, {
            "method": "copernicus-validation",
            "damage_source": metadata,
            "fallback": False,
        }
    return load_demo_buildings(), {
        "method": "fallback",
        "damage_source": metadata,
        "fallback": True,
    }


def _processing_limit(priority: str) -> int:
    return {
        "economy": 60,
        "standard": 120,
        "critical": 180,
    }.get(priority, 120)


def _status_value(status: str | None, *, warning_is_ready: bool = True) -> str:
    if status in {"ready", "configured"}:
        return "ready"
    if warning_is_ready and status == "warning":
        return "ready"
    if status in {"pending", "needs_credentials"}:
        return "pending"
    return "failed"


def _assessment_source_status(readiness: dict) -> DataSourceStatus:
    imagery = readiness.get("imagery") or {}
    return DataSourceStatus(
        osm_buildings=_status_value((readiness.get("osm") or {}).get("status")),
        before_imagery=_status_value((imagery.get("maxar_pre") or {}).get("status")),
        after_imagery=_status_value((imagery.get("maxar_post") or {}).get("status")),
        humanitarian_layers=_status_value((readiness.get("hdx") or {}).get("status")),
        ai_reasoning="pending",
    )


def _load_pipeline_buildings(payload: AssessmentCreate, assessment_id: str, aoi: dict) -> tuple[list, dict]:
    if payload.mode == "live":
        buildings, metadata = run_beirut_imagery_baseline(aoi, assessment_id, limit=_processing_limit(payload.processing_priority))
        if buildings:
            return buildings, metadata
        fallback_buildings, fallback_metadata = load_assessment_buildings()
        return fallback_buildings, {
            "method": "fallback",
            "fallback": True,
            "fallback_reason": metadata,
            "fallback_source": fallback_metadata,
        }
    return load_assessment_buildings()


def dataset_status_snapshot() -> dict:
    settings = get_settings()
    return {
        "xbd_train": validate_dataset_root(settings.xbd_train_root, "train", sample_limit=10),
        "xbd_tier3": validate_dataset_root(settings.xbd_tier3_root, "tier3", sample_limit=10),
    }


async def run_assessment(payload: AssessmentCreate) -> dict:
    started = datetime.now(timezone.utc)
    analysis_settings = get_analysis_settings_state()
    tokenrouter_model = payload.tokenrouter_model or analysis_settings.tokenrouter_model
    normalized_aoi = validate_polygon_aoi(payload.aoi_geojson, require=payload.mode == "live") or DEFAULT_BEIRUT_AOI
    readiness = data_source_status(normalized_aoi, allow_live_osm=payload.mode == "live")
    assessment = AssessmentDetail(
        name=payload.name,
        mode=payload.mode,
        location_name=payload.location_name,
        status=AssessmentStatus.running,
        progress=20,
        created_at=started,
        source_status=_assessment_source_status(readiness),
    )
    buildings, pipeline_metadata = _load_pipeline_buildings(payload, assessment.assessment_id, normalized_aoi)
    fixture = load_beirut_fixture()
    for rank, building in enumerate(sorted(buildings, key=lambda b: b.damage_score, reverse=True), start=1):
        building.priority_rank = rank

    humanitarian_layers = {
        **fixture["humanitarian_layers"],
        "osm": readiness.get("osm"),
        "hdx": readiness.get("hdx"),
    }
    report = await TokenRouterReasoner(model=tokenrouter_model).generate_report(buildings, humanitarian_layers)
    validation = pipeline_metadata.get("validation") or {}
    validation_metrics = validation.get("metrics") or {}
    model_metadata = pipeline_metadata.get("model") or {}
    report.engineering_notes = (
        f"{report.engineering_notes}\n\n"
        f"Pipeline QA: method={pipeline_metadata.get('method', 'unknown')}; "
        f"ML model status={model_metadata.get('status', 'unknown')}; "
        f"validation matched={validation_metrics.get('matched_buildings', 0)} buildings; "
        f"macro F1={validation_metrics.get('macro_f1', 0)}. "
        "Scores require field validation before operational intervention."
    )
    completed = datetime.now(timezone.utc)
    assessment.status = AssessmentStatus.completed
    assessment.progress = 100
    assessment.completed_at = completed
    assessment.runtime_seconds = max(1, int((completed - started).total_seconds()))
    assessment.summary = summarize(buildings)
    assessment.tokenrouter = report.tokenrouter
    assessment.pipeline = {
        **pipeline_metadata,
        "aoi": aoi_metadata(normalized_aoi),
        "source_readiness": readiness,
        "xbd": dataset_status_snapshot(),
        "reasoning_role": "TokenRouter generates humanitarian reasoning/reporting from structured building damage; image damage detection stays server-side.",
    }
    assessment.source_status.ai_reasoning = "ready"

    record = {
        "assessment": assessment.model_dump(mode="json"),
        "request": {**payload.model_dump(mode="json"), "aoi_geojson": normalized_aoi},
        "buildings": [building.model_dump(mode="json") for building in buildings],
        "buildings_geojson": to_feature_collection(buildings),
        "priorities": [priority.model_dump(mode="json") for priority in report.priority_buildings],
        "report": report.model_dump(mode="json"),
        "artifacts": {
            "assessment_id": assessment.assessment_id,
            "method": assessment.pipeline.get("method") if assessment.pipeline else None,
            "aoi": assessment.pipeline.get("aoi") if assessment.pipeline else None,
            "chip_artifacts": pipeline_metadata.get("chip_artifacts", {}),
            "validation": pipeline_metadata.get("validation"),
            "exports": {
                "geojson": f"/api/v1/assessments/{assessment.assessment_id}/exports/geojson",
                "pdf": f"/api/v1/assessments/{assessment.assessment_id}/exports/pdf",
                "docx": f"/api/v1/assessments/{assessment.assessment_id}/exports/docx",
            },
            "pipeline_metadata": pipeline_metadata,
        },
    }
    store.upsert(assessment.assessment_id, record)
    return record


async def ensure_demo_assessment() -> dict:
    existing = store.list()
    if existing:
        return existing[0]
    return await run_assessment(AssessmentCreate())
