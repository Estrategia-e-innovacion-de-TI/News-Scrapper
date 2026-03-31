"""HTTP bootstrap for the SMCP ingestion and tool service."""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException

logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("NEWSRADAR_BACK_URL", "http://localhost:8000").rstrip("/")


async def _post(path: str, payload: dict[str, Any] | None = None, timeout: float = 180.0) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(f"{BACKEND_URL}{path}", json=payload or {})
        response.raise_for_status()
        return response.json()


async def _get(path: str, timeout: float = 30.0) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(f"{BACKEND_URL}{path}")
        response.raise_for_status()
        return response.json()


def create_app() -> FastAPI:
    app = FastAPI(title="NewsRadar SMCP", version="0.2.0")

    @app.get("/health")
    async def health() -> dict[str, Any]:
        backend_health: dict[str, Any] | None = None
        try:
            backend_health = await _get("/api/health")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Backend health probe failed: %s", exc)
        return {
            "status": "ok",
            "mode": "ingestion_runtime",
            "backend_url": BACKEND_URL,
            "backend_health": backend_health,
        }

    @app.get("/tools")
    async def list_tools() -> list[dict[str, Any]]:
        return [
            {"name": "aras_search", "path": "/tools/aras_search", "kind": "search"},
            {"name": "riesgos_search", "path": "/tools/riesgos_search", "kind": "search"},
            {"name": "vigilancia_weekly", "path": "/tools/vigilancia_weekly", "kind": "batch"},
            {"name": "vigilancia_historical", "path": "/tools/vigilancia_historical", "kind": "snapshot"},
            {"name": "extract_news", "path": "/tools/extract_news", "kind": "ingestion"},
        ]

    @app.post("/tools/aras_search")
    async def aras_search(payload: dict[str, Any]) -> dict[str, Any]:
        return await _post("/api/aras/search", payload)

    @app.post("/tools/riesgos_search")
    async def riesgos_search(payload: dict[str, Any]) -> dict[str, Any]:
        return await _post("/api/riesgos/search", payload)

    @app.post("/tools/vigilancia_weekly")
    async def vigilancia_weekly(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = payload or {}
        return await _post("/api/tech-watch/run", body)

    @app.post("/tools/vigilancia_historical")
    async def vigilancia_historical(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = payload or {}
        window_months = int(body.get("window_months", 6))
        force = bool(body.get("force", False))
        return await _post(f"/api/trendmap/generate?window_months={window_months}&force={str(force).lower()}")

    @app.post("/tools/extract_news")
    async def extract_news(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = payload or {}
        focus = body.get("focus")
        if not focus:
            raise HTTPException(status_code=400, detail="focus is required")
        return await _post("/api/pipeline/execute", body, timeout=300.0)

    return app


app = create_app()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import uvicorn

    uvicorn.run("newsradar_server.application.app:app", host="0.0.0.0", port=8080)
