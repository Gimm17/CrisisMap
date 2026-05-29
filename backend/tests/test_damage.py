from app.models.schemas import BuildingDamage
from app.services.geospatial.damage import classify_damage, priority_weight, to_feature_collection
from app.services.geospatial.imagery_baseline import _validation_metrics
from app.services.geospatial.ml_inference import ml_model_status


def test_classify_damage_tiers():
    assert classify_damage(5).value == "intact"
    assert classify_damage(25).value == "minor"
    assert classify_damage(50).value == "moderate"
    assert classify_damage(70).value == "severe"
    assert classify_damage(95).value == "destroyed"


def test_geojson_feature_collection():
    building = BuildingDamage(
        building_id="B-1",
        name="Test Hospital",
        geometry={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
        centroid=(0.5, 0.5),
        damage_score=95,
        damage_tier=classify_damage(95),
        infrastructure_type="Medical Facility",
        population_estimate=1000,
        estimated_cost_usd=1000000,
        confidence=0.9,
    )

    collection = to_feature_collection([building])

    assert collection["type"] == "FeatureCollection"
    assert collection["features"][0]["properties"]["damage_tier"] == "destroyed"
    assert collection["features"][0]["properties"]["inference_method"] == "unknown"
    assert priority_weight(building) > 10


def test_validation_metrics_macro_f1():
    metrics = _validation_metrics([("destroyed", "destroyed"), ("severe", "minor"), ("minor", "minor")])

    assert metrics["matched_buildings"] == 3
    assert 0 <= metrics["macro_f1"] <= 1
    assert metrics["confusion_matrix"]["destroyed"]["destroyed"] == 1


def test_ml_model_status_does_not_crash():
    status = ml_model_status()

    assert "status" in status
    assert status["model"] == "SiamUnet"
