from fastapi import APIRouter, HTTPException

from app.api.responses import success
from app.config import get_settings
from app.core.analysis_settings import get_analysis_settings_state, update_analysis_settings_state
from app.models.schemas import AnalysisSettings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/analysis")
def get_analysis_settings():
    config = get_settings()
    payload = get_analysis_settings_state().model_dump()
    payload["provider_status"] = "configured" if config.tokenrouter_api_key else "missing-key"
    payload["tokenrouter_base_url"] = config.tokenrouter_base_url
    return success(payload, "Analysis settings retrieved")


@router.patch("/analysis")
def update_analysis_settings(payload: AnalysisSettings):
    try:
        state = update_analysis_settings_state(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return success(state.model_dump(), "Analysis settings updated")
