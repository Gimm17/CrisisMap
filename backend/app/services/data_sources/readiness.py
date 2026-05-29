from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.core.store import store
from app.services.data_sources.hdx import summarize_hdx_for_aoi
from app.services.data_sources.osm import summarize_osm_for_aoi
from app.services.geospatial.ml_inference import ml_model_status
from app.services.paths import resolve_project_path
from app.services.xbd.registry import validate_dataset_root


def _path_status(path: object) -> dict[str, Any]:
    resolved = resolve_project_path(path)  # type: ignore[arg-type]
    return {
        "status": "ready" if resolved and resolved.exists() else "missing",
        "path": str(resolved) if resolved else None,
    }


def _raster_status(path: object) -> dict[str, Any]:
    base = _path_status(path)
    if base["status"] != "ready":
        return base
    try:
        import rasterio

        with rasterio.open(base["path"]) as src:
            base.update(
                {
                    "crs": str(src.crs),
                    "bounds": list(src.bounds),
                    "width": src.width,
                    "height": src.height,
                    "bands": src.count,
                }
            )
    except Exception as exc:
        base["status"] = "warning"
        base["message"] = str(exc)
    return base


def data_source_status(aoi: dict[str, Any] | None = None, *, allow_live_osm: bool = False) -> dict[str, Any]:
    settings = get_settings()
    copernicus_ready = bool(settings.copernicus_username and settings.copernicus_password)
    return {
        "postgis": store.status(),
        "osm": summarize_osm_for_aoi(aoi, allow_live=allow_live_osm),
        "hdx": summarize_hdx_for_aoi(aoi),
        "imagery": {
            "maxar_pre": _raster_status(settings.beirut_maxar_pre_path),
            "maxar_post": _raster_status(settings.beirut_maxar_post_path),
            "openaerialmap_post": _raster_status(settings.beirut_oam_post_path),
            "footprints": _path_status(settings.beirut_footprints_path),
            "copernicus_ground_truth": _path_status(settings.beirut_ground_truth_path),
        },
        "xbd": {
            "train": validate_dataset_root(settings.xbd_train_root, "train", sample_limit=5),
            "tier3": validate_dataset_root(settings.xbd_tier3_root, "tier3", sample_limit=5),
        },
        "ml_model": ml_model_status(),
        "tokenrouter": {
            "status": "configured" if settings.tokenrouter_api_key else "missing-key",
            "base_url": settings.tokenrouter_base_url,
            "model": settings.tokenrouter_model,
        },
        "sentinel": {
            "status": "ready" if copernicus_ready else "needs_credentials",
            "source": "Copernicus Data Space",
        },
    }
