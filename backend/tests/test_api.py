from fastapi.testclient import TestClient
import math
import pytest

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_assessment_lifecycle():
    response = client.post("/api/v1/assessments", json={"mode": "demo", "name": "Test Beirut"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assessment_id = payload["data"]["assessment_id"]

    detail = client.get(f"/api/v1/assessments/{assessment_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["status"] == "completed"

    geojson = client.get(f"/api/v1/assessments/{assessment_id}/buildings.geojson")
    assert geojson.status_code == 200
    assert geojson.json()["type"] == "FeatureCollection"

    report = client.get(f"/api/v1/assessments/{assessment_id}/report")
    assert report.status_code == 200
    assert report.json()["data"]["priority_buildings"]

    pdf = client.get(f"/api/v1/assessments/{assessment_id}/exports/pdf")
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")

    docx = client.get(f"/api/v1/assessments/{assessment_id}/exports/docx")
    assert docx.status_code == 200
    assert docx.content.startswith(b"PK")

    artifacts = client.get(f"/api/v1/assessments/{assessment_id}/artifacts")
    assert artifacts.status_code == 200
    assert artifacts.json()["data"]["exports"]["geojson"].endswith("/exports/geojson")

    quality = client.get(f"/api/v1/assessments/{assessment_id}/quality")
    assert quality.status_code == 200
    assert "method" in quality.json()["data"]


def test_data_source_status_endpoint():
    response = client.get("/api/v1/data-sources/status")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "postgis" in data
    assert "imagery" in data
    assert "ml_model" in data
    assert "sentinel" in data


def test_beirut_imagery_metadata_and_tile_endpoint():
    metadata = client.get("/api/v1/imagery/beirut/metadata")
    assert metadata.status_code == 200
    data = metadata.json()["data"]
    assert "before" in data["layers"]
    assert "after" in data["layers"]
    if not data["ready"]:
        pytest.skip("Local Maxar before/after GeoTIFF files are not available")

    z = 14
    x, y = _latlng_to_tile(33.901, 35.518, z)
    tile = client.get(f"/api/v1/imagery/beirut/after/tiles/{z}/{x}/{y}.png")
    assert tile.status_code == 200
    assert tile.headers["content-type"] == "image/png"
    assert tile.content.startswith(b"\x89PNG")

    invalid = client.get(f"/api/v1/imagery/beirut/current/tiles/{z}/{x}/{y}.png")
    assert invalid.status_code == 404


def test_live_assessment_requires_aoi():
    response = client.post("/api/v1/assessments", json={"mode": "live", "name": "No AOI"})
    assert response.status_code == 422
    assert response.json()["error_code"] == "AOI_VALIDATION_ERROR"


def _latlng_to_tile(lat: float, lng: float, z: int) -> tuple[int, int]:
    lat_rad = math.radians(lat)
    n = 2**z
    x = int((lng + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def test_analysis_settings_update():
    payload = {
        "model_profile": "damage",
        "tokenrouter_model": "openai/gpt-5.4",
        "confidence_threshold": 91,
        "processing_priority": "critical",
        "raw_imagery_retention_days": 30,
        "scrub_metadata_on_export": True,
        "auto_publish_destroyed_tags": False,
    }
    response = client.patch("/api/v1/settings/analysis", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["tokenrouter_model"] == "openai/gpt-5.4"
    assert data["confidence_threshold"] == 91
    assert data["auto_publish_destroyed_tags"] is False
