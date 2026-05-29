from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes import assessments, data_sources, datasets, imagery, settings
from app.config import get_settings


def create_app() -> FastAPI:
    config = get_settings()
    app = FastAPI(title=config.app_name, version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(assessments.router, prefix=config.api_prefix)
    app.include_router(data_sources.router, prefix=config.api_prefix)
    app.include_router(datasets.router, prefix=config.api_prefix)
    app.include_router(imagery.router, prefix=config.api_prefix)
    app.include_router(settings.router, prefix=config.api_prefix)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "crisismap-api"}

    return app


app = create_app()
