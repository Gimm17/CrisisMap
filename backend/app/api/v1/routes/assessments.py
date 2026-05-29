from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse

from app.api.responses import error, success
from app.core.store import store
from app.models.schemas import AssessmentCreate
from app.services.exports import build_docx_export, build_pdf_export
from app.services.geospatial.aoi import AoiValidationError
from app.services.pipeline import ensure_demo_assessment, run_assessment

router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.post("")
async def create_assessment(payload: AssessmentCreate):
    try:
        record = await run_assessment(payload)
    except AoiValidationError as exc:
        return JSONResponse(status_code=422, content=error(str(exc), "AOI_VALIDATION_ERROR"))
    return success(record["assessment"], "Assessment completed")


@router.get("")
async def list_assessments(status: str | None = Query(default=None), search: str | None = Query(default=None)):
    records = store.list()
    if not records:
        records = [await ensure_demo_assessment()]
    assessments = [record["assessment"] for record in records]
    if status:
        assessments = [item for item in assessments if item["status"] == status]
    if search:
        needle = search.lower()
        assessments = [
            item
            for item in assessments
            if needle in item["name"].lower() or needle in item["location_name"].lower() or needle in item["assessment_id"].lower()
        ]
    return success(assessments, "Assessment history retrieved", meta={"total": len(assessments)})


@router.get("/{assessment_id}")
async def get_assessment(assessment_id: str):
    record = store.get(assessment_id)
    if not record:
        if assessment_id == "demo":
            record = await ensure_demo_assessment()
        else:
            raise HTTPException(status_code=404, detail="Assessment not found")
    return success(record["assessment"], "Assessment retrieved")


@router.get("/{assessment_id}/buildings.geojson")
async def get_buildings_geojson(assessment_id: str):
    record = store.get(assessment_id)
    if not record:
        record = await ensure_demo_assessment()
    return record["buildings_geojson"]


@router.get("/{assessment_id}/priorities")
async def get_priorities(assessment_id: str):
    record = store.get(assessment_id)
    if not record:
        record = await ensure_demo_assessment()
    return success(record["priorities"], "Priorities retrieved")


@router.get("/{assessment_id}/report")
async def get_report(assessment_id: str):
    record = store.get(assessment_id)
    if not record:
        record = await ensure_demo_assessment()
    return success(record["report"], "Report retrieved")


@router.get("/{assessment_id}/artifacts")
async def get_artifacts(assessment_id: str):
    record = store.get(assessment_id)
    if not record:
        record = await ensure_demo_assessment()
    return success(record.get("artifacts", {}), "Artifacts retrieved")


@router.get("/{assessment_id}/quality")
async def get_assessment_quality(assessment_id: str):
    record = store.get(assessment_id)
    if not record:
        record = await ensure_demo_assessment()
    pipeline = (record.get("assessment") or {}).get("pipeline") or {}
    pipeline_metadata = (record.get("artifacts") or {}).get("pipeline_metadata") or {}
    validation = pipeline_metadata.get("validation") or {}
    return success(
        {
            "assessment_id": assessment_id,
            "method": pipeline.get("method") or pipeline_metadata.get("method"),
            "model": pipeline_metadata.get("model"),
            "method_counts": pipeline_metadata.get("method_counts"),
            "validation": validation,
            "limitations": pipeline_metadata.get("limitations", []),
        },
        "Assessment quality retrieved",
    )


@router.get("/{assessment_id}/artifacts/chips/{building_id}/{kind}.png")
async def get_building_chip(assessment_id: str, building_id: str, kind: str):
    if kind not in {"pre", "post"}:
        raise HTTPException(status_code=404, detail="Unsupported chip type")
    record = store.get(assessment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Assessment not found")
    chip_artifacts = (record.get("artifacts") or {}).get("chip_artifacts") or {}
    chip_path = (chip_artifacts.get(building_id) or {}).get(kind)
    if not chip_path:
        raise HTTPException(status_code=404, detail="Chip artifact not found")
    path = Path(chip_path)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Chip artifact missing on disk")
    return FileResponse(path, media_type="image/png")


@router.get("/{assessment_id}/exports/{kind}")
async def export_assessment(assessment_id: str, kind: str):
    record = store.get(assessment_id)
    if not record:
        record = await ensure_demo_assessment()
    if kind == "geojson":
        return record["buildings_geojson"]
    if kind in {"pdf", "docx"}:
        if kind == "pdf":
            body = build_pdf_export(record["assessment"], record["report"])
            media_type = "application/pdf"
        else:
            body = build_docx_export(record["assessment"], record["report"])
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"{assessment_id}.{kind}"
        return Response(content=body, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    raise HTTPException(status_code=404, detail="Unsupported export type")
