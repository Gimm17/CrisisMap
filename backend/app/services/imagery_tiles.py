from __future__ import annotations

from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

from app.config import get_settings
from app.services.paths import resolve_project_path

ImageryKind = Literal["before", "after"]

TILE_SIZE = 256
WEB_MERCATOR_LIMIT = 20037508.342789244
TRANSPARENT_TILE = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))


def imagery_path(kind: ImageryKind) -> Path | None:
    settings = get_settings()
    configured = settings.beirut_maxar_pre_path if kind == "before" else settings.beirut_maxar_post_path
    resolved = resolve_project_path(configured)
    if not resolved or not resolved.exists():
        return None
    return resolved


def beirut_imagery_metadata() -> dict[str, object]:
    layers = {
        "before": _layer_metadata("before", "Before", "2020-07-31"),
        "after": _layer_metadata("after", "After", "2020-08-05"),
    }
    ready_layers = [layer for layer in layers.values() if layer["status"] == "ready"]
    bounds = _union_bounds([layer.get("bounds") for layer in ready_layers])
    return {
        "ready": len(ready_layers) == 2,
        "tile_size": TILE_SIZE,
        "min_zoom": 11,
        "max_zoom": 18,
        "default_bounds": bounds,
        "attribution": "Maxar Open Data / CrisisMap local imagery",
        "layers": layers,
    }


def render_beirut_tile(kind: ImageryKind, z: int, x: int, y: int) -> bytes:
    path = imagery_path(kind)
    if not path:
        raise FileNotFoundError(f"{kind} imagery is not available")
    mtime = path.stat().st_mtime
    return _render_tile_cached(kind, str(path), mtime, z, x, y)


def _layer_metadata(kind: ImageryKind, label: str, date_label: str) -> dict[str, object]:
    path = imagery_path(kind)
    if not path:
        return {
            "kind": kind,
            "label": label,
            "date_label": date_label,
            "status": "missing",
            "tile_url_template": f"/api/v1/imagery/beirut/{kind}/tiles/{{z}}/{{x}}/{{y}}.png",
        }
    try:
        import rasterio

        with rasterio.open(path) as src:
            bounds = transform_bounds(src.crs, "EPSG:4326", *src.bounds, densify_pts=21)
            return {
                "kind": kind,
                "label": label,
                "date_label": date_label,
                "status": "ready",
                "path": str(path),
                "crs": str(src.crs),
                "bounds": [[bounds[1], bounds[0]], [bounds[3], bounds[2]]],
                "width": src.width,
                "height": src.height,
                "bands": src.count,
                "tile_url_template": f"/api/v1/imagery/beirut/{kind}/tiles/{{z}}/{{x}}/{{y}}.png",
            }
    except Exception as exc:
        return {
            "kind": kind,
            "label": label,
            "date_label": date_label,
            "status": "error",
            "path": str(path),
            "message": str(exc),
            "tile_url_template": f"/api/v1/imagery/beirut/{kind}/tiles/{{z}}/{{x}}/{{y}}.png",
        }


def _union_bounds(bounds_items: list[object]) -> list[list[float]] | None:
    valid = [bounds for bounds in bounds_items if _is_bounds(bounds)]
    if not valid:
        return None
    south = min(float(bounds[0][0]) for bounds in valid)  # type: ignore[index]
    west = min(float(bounds[0][1]) for bounds in valid)  # type: ignore[index]
    north = max(float(bounds[1][0]) for bounds in valid)  # type: ignore[index]
    east = max(float(bounds[1][1]) for bounds in valid)  # type: ignore[index]
    return [[south, west], [north, east]]


def _is_bounds(value: object) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(point, list) and len(point) == 2 for point in value)
    )


@lru_cache(maxsize=4096)
def _render_tile_cached(kind: str, path_str: str, mtime: float, z: int, x: int, y: int) -> bytes:
    import rasterio

    path = Path(path_str)
    bounds = _tile_bounds_3857(z, x, y)
    with rasterio.open(path) as src:
        with WarpedVRT(src, crs="EPSG:3857", resampling=Resampling.bilinear) as vrt:
            if not _intersects(bounds, vrt.bounds):
                return _transparent_tile_bytes()
            indexes = [1, 2, 3] if vrt.count >= 3 else [1]
            window = from_bounds(*bounds, transform=vrt.transform)
            data = vrt.read(
                indexes=indexes,
                window=window,
                out_shape=(len(indexes), TILE_SIZE, TILE_SIZE),
                masked=True,
            )
    return _array_to_png(data)


def _tile_bounds_3857(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    tiles = 2**z
    tile_span = (WEB_MERCATOR_LIMIT * 2) / tiles
    minx = -WEB_MERCATOR_LIMIT + x * tile_span
    maxx = minx + tile_span
    maxy = WEB_MERCATOR_LIMIT - y * tile_span
    miny = maxy - tile_span
    return minx, miny, maxx, maxy


def _intersects(bounds: tuple[float, float, float, float], other: tuple[float, float, float, float]) -> bool:
    minx, miny, maxx, maxy = bounds
    ominx, ominy, omaxx, omaxy = other
    return maxx > ominx and minx < omaxx and maxy > ominy and miny < omaxy


def _array_to_png(data: np.ma.MaskedArray) -> bytes:
    mask = np.ma.getmaskarray(data)
    alpha = (~np.all(mask, axis=0)).astype("uint8") * 255
    if not np.any(alpha):
        return _transparent_tile_bytes()

    rgb = np.ma.filled(data, 0).astype("float32")
    if rgb.shape[0] == 1:
        rgb = np.repeat(rgb, 3, axis=0)
    rgb = rgb[:3]

    valid_values = rgb[:, alpha > 0]
    if valid_values.size:
        high = float(np.nanpercentile(valid_values, 98))
        low = float(np.nanpercentile(valid_values, 2))
    else:
        high = 255.0
        low = 0.0
    if high <= low:
        high = max(float(np.nanmax(rgb)), 1.0)
        low = 0.0
    if high <= 1.5:
        high = 1.0
        low = 0.0
    scaled = np.clip((rgb - low) / max(high - low, 1e-6) * 255, 0, 255).astype("uint8")
    rgba = np.moveaxis(scaled, 0, -1)
    rgba = np.dstack([rgba, alpha])
    image = Image.fromarray(rgba, mode="RGBA")
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _transparent_tile_bytes() -> bytes:
    buffer = BytesIO()
    TRANSPARENT_TILE.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
