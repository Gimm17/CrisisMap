from __future__ import annotations

import json
import logging
from pathlib import Path
from threading import Lock
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


class AssessmentStore:
    """Small JSON-backed store for the demo MVP.

    The Docker setup includes PostgreSQL/PostGIS for the next persistence step,
    but a file store keeps the Beirut demo runnable without local database setup.
    """

    def __init__(self) -> None:
        settings = get_settings()
        settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.path = settings.artifacts_dir / "assessments.json"
        self._lock = Lock()
        self._backend = "json"
        self._db_error: str | None = None
        self._engine = None
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")
        self._connect_postgis()

    def _connect_postgis(self) -> None:
        settings = get_settings()
        if not settings.postgis_enabled:
            self._db_error = "POSTGIS_ENABLED is false"
            return
        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args={"connect_timeout": 2})
            with engine.begin() as connection:
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
                connection.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS crisismap_assessments (
                            assessment_id TEXT PRIMARY KEY,
                            created_at TIMESTAMPTZ NOT NULL,
                            record_json JSONB NOT NULL,
                            aoi_geojson JSONB,
                            aoi_geom geometry(Polygon, 4326)
                        )
                        """
                    )
                )
            self._engine = engine
            self._backend = "postgis"
            self._db_error = None
        except Exception as exc:
            self._backend = "json"
            self._db_error = str(exc)
            logger.info("PostGIS store unavailable, using JSON fallback: %s", exc)

    def _read(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def _aoi_wkt(self, aoi: dict[str, Any] | None) -> str | None:
        if not aoi or aoi.get("type") != "Polygon":
            return None
        ring = aoi.get("coordinates", [[]])[0]
        if len(ring) < 4:
            return None
        coords = ", ".join(f"{float(lon)} {float(lat)}" for lon, lat in ring)
        return f"POLYGON(({coords}))"

    def _upsert_postgis(self, assessment_id: str, payload: dict[str, Any]) -> bool:
        if self._engine is None:
            return False
        try:
            from sqlalchemy import text

            request = payload.get("request") or {}
            aoi = request.get("aoi_geojson")
            aoi_wkt = self._aoi_wkt(aoi)
            created_at = payload.get("assessment", {}).get("created_at")
            with self._engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        INSERT INTO crisismap_assessments (assessment_id, created_at, record_json, aoi_geojson, aoi_geom)
                        VALUES (
                            :assessment_id,
                            COALESCE(CAST(:created_at AS TIMESTAMPTZ), NOW()),
                            CAST(:record_json AS JSONB),
                            CAST(:aoi_geojson AS JSONB),
                            CASE WHEN :aoi_wkt IS NULL THEN NULL ELSE ST_GeomFromText(:aoi_wkt, 4326) END
                        )
                        ON CONFLICT (assessment_id) DO UPDATE SET
                            created_at = EXCLUDED.created_at,
                            record_json = EXCLUDED.record_json,
                            aoi_geojson = EXCLUDED.aoi_geojson,
                            aoi_geom = EXCLUDED.aoi_geom
                        """
                    ),
                    {
                        "assessment_id": assessment_id,
                        "created_at": created_at,
                        "record_json": json.dumps(payload, default=str),
                        "aoi_geojson": json.dumps(aoi, default=str) if aoi else None,
                        "aoi_wkt": aoi_wkt,
                    },
                )
            return True
        except Exception as exc:
            self._backend = "json"
            self._db_error = str(exc)
            logger.warning("PostGIS upsert failed, keeping JSON fallback active: %s", exc)
            return False

    def _read_postgis(self, assessment_id: str) -> dict[str, Any] | None:
        if self._engine is None:
            return None
        try:
            from sqlalchemy import text

            with self._engine.connect() as connection:
                row = connection.execute(
                    text("SELECT record_json FROM crisismap_assessments WHERE assessment_id = :assessment_id"),
                    {"assessment_id": assessment_id},
                ).mappings().first()
            return dict(row["record_json"]) if row else None
        except Exception as exc:
            self._backend = "json"
            self._db_error = str(exc)
            return None

    def _list_postgis(self) -> list[dict[str, Any]] | None:
        if self._engine is None:
            return None
        try:
            from sqlalchemy import text

            with self._engine.connect() as connection:
                rows = connection.execute(
                    text("SELECT record_json FROM crisismap_assessments ORDER BY created_at DESC LIMIT 200")
                ).mappings().all()
            return [dict(row["record_json"]) for row in rows]
        except Exception as exc:
            self._backend = "json"
            self._db_error = str(exc)
            return None

    def upsert(self, assessment_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            data = self._read()
            data[assessment_id] = payload
            self._write(data)
            self._upsert_postgis(assessment_id, payload)
            return payload

    def get(self, assessment_id: str) -> dict[str, Any] | None:
        record = self._read_postgis(assessment_id)
        if record is not None:
            return record
        with self._lock:
            return self._read().get(assessment_id)

    def list(self) -> list[dict[str, Any]]:
        records = self._list_postgis()
        if records is not None:
            return records
        with self._lock:
            records = list(self._read().values())
        return sorted(records, key=lambda item: item.get("created_at", ""), reverse=True)

    def status(self) -> dict[str, Any]:
        return {
            "status": "ready" if self._backend == "postgis" else "fallback",
            "backend": self._backend,
            "json_path": str(self.path),
            "database_error": self._db_error,
        }


store = AssessmentStore()
