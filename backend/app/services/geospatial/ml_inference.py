from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.services.paths import resolve_project_path


CLASS_NAMES = ["background", "no-damage", "minor-damage", "major-damage", "destroyed"]
CLASS_TO_SCORE = {
    "background": 0,
    "no-damage": 8,
    "minor-damage": 32,
    "major-damage": 68,
    "destroyed": 94,
}


@dataclass(frozen=True)
class DamageModelPrediction:
    damage_score: int
    predicted_class: str
    confidence: float
    probabilities: dict[str, float]
    model_version: str


def ml_model_status() -> dict[str, Any]:
    settings = get_settings()
    checkpoint_path = resolve_project_path(settings.ml_model_checkpoint_path)
    definition_path = resolve_project_path(settings.ml_model_definition_path)
    status: dict[str, Any] = {
        "enabled": settings.ml_model_enabled,
        "status": "disabled" if not settings.ml_model_enabled else "ready",
        "device": settings.ml_model_device,
        "checkpoint_path": str(checkpoint_path) if checkpoint_path else None,
        "definition_path": str(definition_path) if definition_path else None,
        "model": "SiamUnet",
    }
    if not settings.ml_model_enabled:
        return status
    if not checkpoint_path or not checkpoint_path.exists():
        status.update({"status": "missing-checkpoint", "message": "ML checkpoint file is not available"})
        return status
    if not definition_path or not definition_path.exists():
        status.update({"status": "missing-definition", "message": "SiamUnet definition file is not available"})
        return status
    try:
        import torch  # noqa: F401
    except Exception as exc:
        status.update({"status": "missing-dependency", "message": f"PyTorch unavailable: {exc}"})
    return status


def predict_building_damage(
    pre_path: Path,
    post_path: Path,
    bbox: tuple[float, float, float, float],
    *,
    baseline_score: int,
) -> DamageModelPrediction | None:
    model_bundle = _load_model_bundle()
    if not model_bundle:
        return None
    torch = model_bundle["torch"]
    model = model_bundle["model"]
    device = model_bundle["device"]
    pre_tensor, post_tensor = _read_model_tensors(pre_path, post_path, bbox, torch, device)
    with torch.no_grad():
        _, _, damage_logits = model(pre_tensor, post_tensor)
        probabilities_tensor = torch.softmax(damage_logits, dim=1).mean(dim=(0, 2, 3)).detach().cpu()
    probabilities = {
        class_name: round(float(probabilities_tensor[index]), 6)
        for index, class_name in enumerate(CLASS_NAMES)
    }
    raw_score = sum(probabilities[class_name] * CLASS_TO_SCORE[class_name] for class_name in CLASS_NAMES)
    # The public checkpoint was trained on xBD tiles, not Beirut Maxar footprints.
    # Blend with image-change baseline to reduce overconfident domain-transfer spikes.
    damage_score = int(round((raw_score * 0.7) + (baseline_score * 0.3)))
    damage_score = max(0, min(100, damage_score))
    damage_classes = CLASS_NAMES[1:]
    predicted_class = max(damage_classes, key=lambda class_name: probabilities[class_name])
    confidence = max(probabilities[class_name] for class_name in damage_classes)
    return DamageModelPrediction(
        damage_score=damage_score,
        predicted_class=predicted_class,
        confidence=round(max(0.35, min(0.98, confidence)), 3),
        probabilities=probabilities,
        model_version=model_bundle["model_version"],
    )


@lru_cache(maxsize=1)
def _load_model_bundle() -> dict[str, Any] | None:
    status = ml_model_status()
    if status.get("status") != "ready":
        return None
    settings = get_settings()
    checkpoint_path = resolve_project_path(settings.ml_model_checkpoint_path)
    definition_path = resolve_project_path(settings.ml_model_definition_path)
    if not checkpoint_path or not definition_path:
        return None
    try:
        import torch

        module_spec = importlib.util.spec_from_file_location("crisismap_siam_unet", definition_path)
        if module_spec is None or module_spec.loader is None:
            return None
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        model = module.SiamUnet()
        try:
            checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        except TypeError:
            checkpoint = torch.load(checkpoint_path, map_location="cpu")
        state_dict = _extract_state_dict(checkpoint)
        load_result = model.load_state_dict(state_dict, strict=False)
        if not state_dict or (load_result.missing_keys and len(load_result.missing_keys) > len(state_dict)):
            return None
        device = _resolve_torch_device(torch, settings.ml_model_device)
        model.to(device)
        model.eval()
        return {
            "torch": torch,
            "model": model,
            "device": device,
            "model_version": f"SiamUnet:{checkpoint_path.name}",
            "missing_keys": list(load_result.missing_keys),
            "unexpected_keys": list(load_result.unexpected_keys),
        }
    except Exception:
        return None


def _extract_state_dict(checkpoint: Any) -> dict[str, Any]:
    if isinstance(checkpoint, dict):
        state_dict = checkpoint.get("state_dict") or checkpoint.get("model_state_dict") or checkpoint.get("model") or checkpoint
    else:
        state_dict = checkpoint
    if not isinstance(state_dict, dict):
        return {}
    cleaned: dict[str, Any] = {}
    for key, value in state_dict.items():
        next_key = str(key)
        for prefix in ("module.", "model."):
            if next_key.startswith(prefix):
                next_key = next_key[len(prefix) :]
        cleaned[next_key] = value
    return cleaned


def _resolve_torch_device(torch: Any, requested_device: str):
    if requested_device.startswith("cuda") and torch.cuda.is_available():
        return torch.device(requested_device)
    return torch.device("cpu")


def _read_model_tensors(
    pre_path: Path,
    post_path: Path,
    bbox: tuple[float, float, float, float],
    torch: Any,
    device: Any,
):
    import numpy as np
    import rasterio
    from rasterio.windows import from_bounds

    arrays = []
    for path in (pre_path, post_path):
        with rasterio.open(path) as src:
            window = from_bounds(*bbox, transform=src.transform).round_offsets().round_lengths()
            data = src.read(indexes=[1, 2, 3], window=window, out_shape=(3, 256, 256), boundless=True, fill_value=0)
        data = data.astype("float32")
        scale = max(float(np.percentile(data, 99)), 255.0)
        data = np.clip(data / scale, 0.0, 1.0)
        arrays.append(torch.from_numpy(data).unsqueeze(0).to(device))
    return arrays[0], arrays[1]
