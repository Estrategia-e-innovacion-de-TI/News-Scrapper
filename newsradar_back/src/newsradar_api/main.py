"""FastAPI application entry point with PostgreSQL."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from newsradar_api.domains.aras_search.entry_points.router import router as aras_audit_router
from newsradar_api.domains.risk_mapping.entry_points.router import router as riskmap_router
from newsradar_api.domains.subscriptions.entry_points.router import router as subscriptions_domain_router
from newsradar_api.domains.tech_watch.entry_points.router import router as tech_watch_router
from newsradar_api.domains.trend_mapping.entry_points.router import router as trendmap_domain_router
from newsradar_api.infrastructure.entry_points.aras_routes import router as aras_router
from newsradar_api.infrastructure.entry_points.riesgos_routes import router as riesgos_router
from newsradar_api.infrastructure.entry_points.vigilancia_routes import router as vigilancia_router
from newsradar_api.infrastructure.entry_points.trendmap_routes import router as trendmap_router
from newsradar_api.infrastructure.entry_points.chat_ws import router as chat_router
from newsradar_api.infrastructure.entry_points.pipeline_routes import router as pipeline_router
from newsradar_api.infrastructure.entry_points.subscription_routes import router as subscription_router
from newsradar_api.infrastructure.entry_points.catalog_routes import router as catalog_router
from newsradar_api.infrastructure.entry_points.export_routes import router as export_router
from newsradar_api.shared_kernel.observability.router import router as observability_router
from newsradar_api.infrastructure.driven_adapters.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


def create_app() -> FastAPI:
    application = FastAPI(title="News Radar API", version="0.1.0", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(aras_router, prefix="/api/aras", tags=["ARAS"])
    application.include_router(aras_audit_router, prefix="/api/aras", tags=["ARAS"])
    application.include_router(riesgos_router, prefix="/api/riesgos", tags=["Riesgos"])
    application.include_router(vigilancia_router, prefix="/api/vigilancia", tags=["Vigilancia"])
    application.include_router(tech_watch_router, prefix="/api/tech-watch", tags=["Tech Watch"])
    application.include_router(trendmap_router, prefix="/api/trendmap", tags=["Trendmap"])
    application.include_router(trendmap_domain_router, prefix="/api/trendmap", tags=["Trendmap"])
    application.include_router(riskmap_router, prefix="/api/riskmap", tags=["Risk Mapping"])
    application.include_router(chat_router, prefix="/api", tags=["Chat"])
    application.include_router(pipeline_router, prefix="/api/pipeline", tags=["Pipeline"])
    application.include_router(subscription_router, prefix="/api/subscriptions", tags=["Subscriptions"])
    application.include_router(subscriptions_domain_router, prefix="/api/subscriptions", tags=["Subscriptions"])
    application.include_router(catalog_router, prefix="/api/catalog", tags=["Catalog"])
    application.include_router(export_router, prefix="/api/export", tags=["Export"])
    application.include_router(observability_router, prefix="/api", tags=["Infra"])
    return application


app = create_app()
