"""Batch ingestion runtime with SMCP-first execution and local fallback."""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def _smcp_enabled() -> bool:
    return os.getenv("NEWSRADAR_USE_SMCP", "1").lower() not in {"0", "false", "no"}


def _smcp_url() -> str:
    return os.getenv("NEWSRADAR_SMCP_URL", "http://localhost:8080").rstrip("/")


def _normalize_terms(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip()) or None
    return str(value)


def _build_payload(run_id: str, focus: str | None, params: dict[str, Any]) -> dict[str, Any]:
    payload = dict(params)
    payload["run_id"] = run_id
    payload["focus"] = focus
    payload["adhoc"] = bool(payload.get("adhoc", False))
    payload["terms"] = _normalize_terms(payload.get("terms"))
    return payload


async def run_local_ingestion(run_id: str, focus: str | None, **params: Any) -> dict[str, Any]:
    from newsradar_api.infrastructure.pipeline.pipeline import run_extraction

    payload = _build_payload(run_id, focus, params)
    final_state = await run_extraction(
        run_id=run_id,
        catalog_path=payload.get("catalog_path", "catalog.yaml"),
        days=int(payload.get("days", 7)),
        max_items_per_source=int(payload.get("max_items_per_source", 20)),
        out_dir=payload.get("out_dir", "out"),
        debug=bool(payload.get("debug", False)),
        dry_run=bool(payload.get("dry_run", False)),
        only_source=payload.get("only_source"),
        no_playwright=bool(payload.get("no_playwright", False)),
        focus=focus,
        adhoc=bool(payload.get("adhoc", False)),
        company=payload.get("company"),
        terms=payload.get("terms"),
        date_from=payload.get("date_from"),
        date_to=payload.get("date_to"),
        topk_per_source=int(payload.get("topk_per_source", 5)),
        max_candidates_total=int(payload.get("max_candidates_total", 50)),
        candidates_path=payload.get("candidates_path"),
        classifier_mode=payload.get("classifier_mode", "rules"),
        nit=payload.get("nit"),
        terms_preset=payload.get("terms_preset"),
    )
    return {
        "status": "completed",
        "run_id": final_state.run_id,
        "execution_id": final_state.execution_id,
    }


async def run_smcp_ingestion(run_id: str, focus: str | None, **params: Any) -> dict[str, Any]:
    payload = _build_payload(run_id, focus, params)
    url = f"{_smcp_url()}/tools/extract_news"
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
    if "run_id" not in data:
        data["run_id"] = run_id
    return data


async def run_ingestion_with_fallback(run_id: str, focus: str | None, **params: Any) -> dict[str, Any]:
    if _smcp_enabled():
        try:
            logger.info("Dispatching ingestion to SMCP for focus=%s run_id=%s", focus, run_id)
            return await run_smcp_ingestion(run_id, focus, **params)
        except Exception as exc:
            logger.warning(
                "SMCP ingestion unavailable for focus=%s run_id=%s; using local fallback: %s",
                focus,
                run_id,
                exc,
            )
    logger.info("Running local ingestion fallback for focus=%s run_id=%s", focus, run_id)
    return await run_local_ingestion(run_id, focus, **params)
