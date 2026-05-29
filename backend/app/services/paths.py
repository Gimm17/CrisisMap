from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_project_path(path: Path | str | None) -> Path | None:
    if path is None:
        return None
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    root = project_root()
    backend = backend_root()
    for base in (Path.cwd(), backend, root):
        resolved = (base / candidate).resolve()
        if resolved.exists():
            return resolved
    return (root / candidate).resolve()

