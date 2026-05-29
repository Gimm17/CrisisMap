from pathlib import Path
from threading import Lock

from app.config import get_settings
from app.models.schemas import AnalysisSettings

TOKENROUTER_MODELS = [
    "anthropic/claude-sonnet-4.6",
    "openai/gpt-5.4",
    "moonshotai/kimi-k2.6",
    "google/gemini-3.1-pro-preview",
    "x-ai/grok-4.20-beta",
]

_lock = Lock()


def _settings_path() -> Path:
    settings = get_settings()
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    return settings.artifacts_dir / "analysis_settings.json"


def _load_settings() -> AnalysisSettings:
    path = _settings_path()
    if path.exists():
        try:
            return AnalysisSettings.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return AnalysisSettings(tokenrouter_model=get_settings().tokenrouter_model)


def _save_settings(settings: AnalysisSettings) -> None:
    _settings_path().write_text(settings.model_dump_json(indent=2), encoding="utf-8")


_settings_state = _load_settings()


def get_analysis_settings_state() -> AnalysisSettings:
    with _lock:
        return _settings_state


def update_analysis_settings_state(payload: AnalysisSettings) -> AnalysisSettings:
    global _settings_state
    if payload.tokenrouter_model not in TOKENROUTER_MODELS:
        raise ValueError("Unsupported TokenRouter model")
    with _lock:
        _settings_state = payload
        _save_settings(_settings_state)
        return _settings_state
