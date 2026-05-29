# CrisisMap Public Data Downloads

Generated on 2026-05-19 for the Beirut Port AOI:

- BBox lon/lat: `35.48,33.85,35.55,33.90`
- CRS: `EPSG:4326`
- Machine manifest: `data/public_data_download_manifest.json`
- Raw data folder: `data/raw/`

## Downloaded Automatically

Core imagery:

- `data/raw/imagery/maxar/beirut_explosion/pre_event_2020-07-31_10300500A5F95600.tif`
- `data/raw/imagery/maxar/beirut_explosion/post_event_2020-08-05_104001005EBCEB00.tif`
- `data/raw/imagery/maxar/beirut_explosion/preview_ortho_0731.tif`
- `data/raw/imagery/maxar/beirut_explosion/preview_ortho_0805.tif`
- `data/raw/imagery/openaerialmap/beirut_aoi/post_event_uav_2020-08-05_beirut_port_012m.tif`
- `data/raw/imagery/openaerialmap/beirut_aoi/oam_metadata_beirut_2020.json`

Vector and validation data:

- `data/raw/vector/maxar/beirut_explosion/Beirut_2D_Footprints.zip`
- `data/raw/vector/maxar/beirut_explosion/extracted/Beirut-Explosion-2D-building-32636/Beirut-Explosion-2D-building-32636.shp`
- `data/raw/vector/osm/beirut_aoi/overpass_beirut_infrastructure.json`
- `data/raw/ground_truth/copernicus_ems/EMSR452/EMSR452_AOI01_GRA_PRODUCT_r1_RTP01_v2_vector.zip`
- `data/raw/ground_truth/copernicus_ems/EMSR452/extracted/EMSR452_AOI01_GRA_PRODUCT_observedEventP_r1_v2.shp`
- `data/raw/ground_truth/copernicus_ems/EMSR452/extracted/EMSR452_AOI01_GRA_PRODUCT_builtUpP_r1_v2.shp`

Humanitarian exposure data:

- `data/raw/humanitarian/hdx/lebanon_healthsites/lebanon_healthsites.geojson`
- `data/raw/humanitarian/hdx/lebanon_healthsites/lebanon_healthsites_package.json`
- `data/raw/population/worldpop/LBN/2020/lbn_ppp_2020.tif`
- `data/raw/population/worldpop/LBN/2020/worldpop_lbn_wpgp_index.json`

Baseline model:

- `data/raw/models/microsoft_building_damage_assessment_cnn_siamese/model_best.pth.tar`
- `data/raw/models/microsoft_building_damage_assessment_cnn_siamese/end_to_end_Siam_UNet.py`
- `data/raw/models/microsoft_building_damage_assessment_cnn_siamese/README.md`
- `data/raw/models/microsoft_building_damage_assessment_cnn_siamese/LICENSE`

## Manual Or Credentialed Data Still Needed

- xBD/xView2 dataset: required for evaluation/fine-tuning; access usually requires account/Kaggle/manual terms acceptance.
- ACLED conflict-event data: requires registered ACLED API credentials.
- Copernicus Data Space Sentinel-1/Sentinel-2 full products: public data, but full product download usually needs a Copernicus account.
- Any commercial imagery outside Maxar/OpenAerialMap open-data disaster releases.

## Current Notes

- Downloaded data size is about 1.41 GB.
- The OSM Overpass AOI file contains 47,777 elements.
- `data/raw/` is intentionally ignored by git; rerun `scripts/download_public_beirut_data.ps1` to recreate it.
