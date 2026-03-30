"""FastAPI application entry point.

Creates the FastAPI app, registers routers, and configures middleware.
"""
from __future__ import annotations

from fastapi import FastAPI

from newsradar_api.infrastructure.entry_points.aras_routes import router as aras_router
from newsradar_api.infrastructure.entry_points.riesgos_routes import router as riesgos_router
from newsradar_api.infrastructure.entry_points.vigilancia_routes import router as vigilancia_router
from newsradar_api.infrastructure.entry_points.chat_ws import router as chat_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns
    -------
    FastAPI
        Configured application instance with all routers registered.
    """
    application = FastAPI(
        title="News Radar API",
        description="Backend API for ARAS, Riesgos Emergentes, and Vigilancia Tecnológica",
        version="0.1.0",
    )

    application.include_router(aras_router, prefix="/api/aras", tags=["ARAS"])
    application.include_router(riesgos_router, prefix="/api/riesgos", tags=["Riesgos"])
    application.include_router(vigilancia_router, prefix="/api/vigilancia", tags=["Vigilancia"])
    application.include_router(chat_router, prefix="/api", tags=["Chat"])

    return application


app = create_app()
