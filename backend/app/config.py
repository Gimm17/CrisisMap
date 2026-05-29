from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CrisisMap API"
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    tokenrouter_api_key: str | None = None
    tokenrouter_base_url: str = "https://api.tokenrouter.com/v1"
    tokenrouter_model: str = "anthropic/claude-sonnet-4.6"

    database_url: str = "postgresql+psycopg://crisismap:crisismap@localhost:5432/crisismap"
    postgis_enabled: bool = True
    overpass_url: str = "https://overpass-api.de/api/interpreter"

    data_dir: Path = Path("../data")
    demo_fixture_dir: Path = Path("../data/fixtures/beirut")
    artifacts_dir: Path = Path("./artifacts")
    crisismap_data_root: Path | None = Path("E:/CrisisMapData")
    xbd_train_root: Path | None = Path("E:/CrisisMapData/xbd/extracted/train/train")
    xbd_tier3_root: Path | None = Path("E:/CrisisMapData/xbd/extracted/tier3/tier3")
    beirut_ground_truth_path: Path = Path(
        "../data/raw/ground_truth/copernicus_ems/EMSR452/extracted/EMSR452_AOI01_GRA_PRODUCT_builtUpP_r1_v2.json"
    )
    hdx_local_root: Path = Path("../data/raw/humanitarian/hdx")
    worldpop_index_path: Path = Path("../data/raw/population/worldpop/LBN/2020/worldpop_lbn_wpgp_index.json")
    beirut_maxar_pre_path: Path = Path("../data/raw/imagery/maxar/beirut_explosion/pre_event_2020-07-31_10300500A5F95600.tif")
    beirut_maxar_post_path: Path = Path("../data/raw/imagery/maxar/beirut_explosion/post_event_2020-08-05_104001005EBCEB00.tif")
    beirut_footprints_path: Path = Path(
        "../data/raw/vector/maxar/beirut_explosion/extracted/Beirut-Explosion-2D-building-32636/Beirut-Explosion-2D-building-32636.shp"
    )
    beirut_oam_post_path: Path = Path("../data/raw/imagery/openaerialmap/beirut_aoi/post_event_uav_2020-08-05_beirut_port_012m.tif")
    osm_overpass_local_path: Path = Path("../data/raw/vector/osm/beirut_aoi/overpass_beirut_infrastructure.json")
    copernicus_username: str | None = None
    copernicus_password: str | None = None
    beirut_max_buildings: int = 300
    ml_model_enabled: bool = True
    ml_model_checkpoint_path: Path = Path("../data/raw/models/microsoft_building_damage_assessment_cnn_siamese/model_best.pth.tar")
    ml_model_definition_path: Path = Path("../data/raw/models/microsoft_building_damage_assessment_cnn_siamese/end_to_end_Siam_UNet.py")
    ml_model_device: str = "cpu"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
