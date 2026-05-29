from fastapi import APIRouter, HTTPException, Response

from app.api.responses import success
from app.services.imagery_tiles import beirut_imagery_metadata, render_beirut_tile

router = APIRouter(prefix="/imagery", tags=["imagery"])


@router.get("/beirut/metadata")
async def get_beirut_imagery_metadata():
    return success(beirut_imagery_metadata(), "Beirut imagery metadata retrieved")


@router.get("/beirut/{kind}/tiles/{z}/{x}/{y}.png")
async def get_beirut_imagery_tile(kind: str, z: int, x: int, y: int):
    if kind not in {"before", "after"}:
        raise HTTPException(status_code=404, detail="Unsupported imagery kind")
    try:
        body = render_beirut_tile(kind, z, x, y)  # type: ignore[arg-type]
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=body,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )
