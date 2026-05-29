from typing import Any

from fastapi import APIRouter

from app.api.responses import success
from app.services.data_sources.readiness import data_source_status
from app.services.geospatial.aoi import DEFAULT_BEIRUT_AOI

router = APIRouter(prefix="/data-sources", tags=["data-sources"])


@router.get("/status")
async def get_data_source_status() -> dict[str, Any]:
    return success(data_source_status(DEFAULT_BEIRUT_AOI), "Data source status retrieved")
