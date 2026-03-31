"""Canonical ARAS/Riesgos ad-hoc audit endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from newsradar_api.domains.aras_search.application import service
from newsradar_api.infrastructure.driven_adapters.database import get_session

router = APIRouter()


@router.get("/search/history")
async def search_history(session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = await service.history(session)
    return [
        {
            "search_id": str(row.id),
            "search_kind": row.search_kind,
            "query_mode": row.query_mode,
            "company": row.company,
            "issuer": row.issuer,
            "term": row.term,
            "date_from": row.date_from.isoformat() if row.date_from else None,
            "date_to": row.date_to.isoformat() if row.date_to else None,
            "results_count": row.results_count,
            "export_id": str(row.export_id) if row.export_id else None,
            "requested_at": row.requested_at.isoformat(),
        }
        for row in rows
    ]


@router.get("/search/{search_id}")
async def get_search(search_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    row = await service.get_search(session, search_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Search not found")
    return {
        "search_id": str(row.id),
        "search_kind": row.search_kind,
        "query_mode": row.query_mode,
        "parameters": row.parameters_json or {},
        "results": row.results_json or [],
        "results_count": row.results_count,
        "export_id": str(row.export_id) if row.export_id else None,
    }


@router.get("/export/{export_id}")
async def get_export(export_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    row = await service.get_export(session, export_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Export not found")
    return {
        "export_id": str(row.id),
        "export_kind": row.export_kind,
        "file_name": row.file_name,
        "file_path": row.file_path,
        "status": row.status,
        "row_count": row.row_count,
        "metadata": row.metadata_json or {},
    }
