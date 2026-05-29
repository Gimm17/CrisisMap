from fastapi import APIRouter, Query

from app.api.responses import success
from app.config import get_settings
from app.services.xbd.baseline import ImageChangeDamageModel, load_pair_from_manifest_record, summarize_predictions
from app.services.xbd.registry import build_manifest_for_roots, validate_dataset_root, write_manifest

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("/xbd/status")
def get_xbd_status(sample_limit: int = Query(default=25, ge=0, le=500)):
    settings = get_settings()
    limit = None if sample_limit == 0 else sample_limit
    data = {
        "train": validate_dataset_root(settings.xbd_train_root, "train", sample_limit=limit),
        "tier3": validate_dataset_root(settings.xbd_tier3_root, "tier3", sample_limit=limit),
    }
    return success(data, "xBD dataset status retrieved")


@router.post("/xbd/manifest")
def create_xbd_manifest(
    sample_limit: int = Query(default=500, ge=0, le=20000),
    write_artifact: bool = Query(default=True),
):
    settings = get_settings()
    limit = None if sample_limit == 0 else sample_limit
    manifest = build_manifest_for_roots(
        {
            "train": settings.xbd_train_root,
            "tier3": settings.xbd_tier3_root,
        },
        sample_limit=limit,
    )
    meta = {"artifact_path": None}
    if write_artifact:
        meta["artifact_path"] = str(write_manifest(manifest, settings.artifacts_dir))
    return success(manifest, "xBD manifest generated", meta=meta)


@router.post("/xbd/baseline-sample")
def run_xbd_baseline_sample(max_buildings: int = Query(default=25, ge=1, le=200)):
    settings = get_settings()
    manifest = build_manifest_for_roots({"train": settings.xbd_train_root}, sample_limit=1)
    if not manifest["tiles"]:
        return success(
            {"predictions": [], "summary": {}, "manifest": manifest},
            "No xBD sample is available. Check XBD_TRAIN_ROOT.",
        )
    pair = load_pair_from_manifest_record(manifest["tiles"][0])
    predictions = ImageChangeDamageModel().predict_pair(pair, max_buildings=max_buildings)
    return success(
        {
            "tile_id": pair.tile_id,
            "summary": summarize_predictions(predictions),
            "predictions": [prediction.__dict__ for prediction in predictions],
        },
        "xBD baseline inference sample completed",
    )

