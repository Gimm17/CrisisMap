import json
from pathlib import Path

from PIL import Image

from app.services.xbd.baseline import ImageChangeDamageModel, summarize_predictions
from app.services.xbd.preprocessing import extract_xbd_polygons, label_summary
from app.services.xbd.registry import build_manifest_for_roots, discover_tile_pairs, validate_dataset_root


def _write_label(path: Path, img_name: str, subtype: str = "major-damage") -> None:
    payload = {
        "features": {
            "lng_lat": [
                {
                    "properties": {"feature_type": "building", "subtype": subtype, "uid": "u-1"},
                    "wkt": "POLYGON ((35.1 33.1, 35.2 33.1, 35.2 33.2, 35.1 33.1))",
                }
            ],
            "xy": [
                {
                    "properties": {"feature_type": "building", "subtype": subtype, "uid": "u-1"},
                    "wkt": "POLYGON ((10 10, 48 10, 48 48, 10 48, 10 10))",
                }
            ],
        },
        "metadata": {
            "disaster": "unit-disaster",
            "disaster_type": "earthquake",
            "sensor": "WORLDVIEW03_VNIR",
            "gsd": 0.5,
            "width": 64,
            "height": 64,
            "img_name": img_name,
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _make_xbd_fixture(root: Path) -> Path:
    dataset = root / "train"
    images = dataset / "images"
    labels = dataset / "labels"
    images.mkdir(parents=True)
    labels.mkdir(parents=True)
    Image.new("RGB", (64, 64), (20, 20, 20)).save(images / "unit_00000000_pre_disaster.png")
    Image.new("RGB", (64, 64), (220, 220, 220)).save(images / "unit_00000000_post_disaster.png")
    _write_label(labels / "unit_00000000_pre_disaster.json", "unit_00000000_pre_disaster.png", "no-damage")
    _write_label(labels / "unit_00000000_post_disaster.json", "unit_00000000_post_disaster.png", "major-damage")
    return dataset


def test_xbd_registry_manifest_and_validation(tmp_path):
    dataset = _make_xbd_fixture(tmp_path)
    pairs, status = discover_tile_pairs(dataset, "train")

    assert status["paired_tiles"] == 1
    assert not status["missing_pairs"]
    assert len(pairs) == 1

    validation = validate_dataset_root(dataset, "train", sample_limit=None)
    assert validation["valid"] is True
    assert validation["sampled_tiles"] == 1

    manifest = build_manifest_for_roots({"train": dataset}, sample_limit=None)
    assert manifest["record_count"] == 1
    assert manifest["tiles"][0]["building_count"] == 1
    assert manifest["tiles"][0]["damage_counts"]["major-damage"] == 1


def test_xbd_label_preprocessing_and_baseline(tmp_path):
    dataset = _make_xbd_fixture(tmp_path)
    pairs, _ = discover_tile_pairs(dataset, "train")
    polygons = extract_xbd_polygons(pairs[0].post_label)
    summary = label_summary(pairs[0].post_label)

    assert polygons[0].bbox_xy == (10.0, 10.0, 48.0, 48.0)
    assert polygons[0].damage_class == 3
    assert summary["disaster"] == "unit-disaster"

    predictions = ImageChangeDamageModel().predict_pair(pairs[0], max_buildings=1)
    assert predictions[0].damage_score >= 58
    assert predictions[0].predicted_subtype in {"major-damage", "destroyed"}
    assert summarize_predictions(predictions)["building_count"] == 1

