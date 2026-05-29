from typing import Any


def success(data: Any = None, message: str = "OK", meta: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"success": True, "message": message, "data": data}
    if meta is not None:
        payload["meta"] = meta
    return payload


def error(message: str, error_code: str, errors: Any = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"success": False, "message": message, "error_code": error_code}
    if errors is not None:
        payload["errors"] = errors
    return payload
