"""Excel export REST endpoints.

POST /api/export/excel          — generate .xlsx from run_id, return FileResponse
GET  /api/export/download/{name} — download a previously generated .xlsx

Validates: Requirements 12.1-12.6
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from tempfile import gettempdir

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from newsradar_api.infrastructure.driven_adapters.database import get_session
from newsradar_api.infrastructure.driven_adapters.db_models import (
    Document as DBDocument,
    ExportAudit,
    PipelineRun,
)

logger = logging.getLogger(__name__)
router = APIRouter()

EXPORT_DIR = Path(gettempdir()) / "newsradar_exports"


class ExcelExportRequest(BaseModel):
    """Request body for POST /api/export/excel."""
    run_id: str = Field(..., description="Pipeline run ID to export")
    filters: dict | None = Field(None, description="Optional filters (category, severity, etc.)")


@router.post("/excel")
async def export_excel(
    request: ExcelExportRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Generate an Excel report for a pipeline run.

    Fetches documents from the DB by run_id, applies optional filters,
    generates .xlsx with ExcelExporter, and returns the download URL.

    Validates: Requirements 12.1-12.6
    """
    run_id = request.run_id
    logger.info("POST /api/export/excel — run_id=%s", run_id)

    # Fetch documents for this run
    stmt = select(DBDocument).where(DBDocument.run_id == run_id)

    # Apply optional filters
    if request.filters:
        if "category" in request.filters:
            stmt = stmt.where(DBDocument.category == request.filters["category"])
        if "severity" in request.filters:
            stmt = stmt.where(DBDocument.severity == request.filters["severity"])
        if "min_score" in request.filters:
            stmt = stmt.where(DBDocument.relevance_score >= request.filters["min_score"])

    stmt = stmt.order_by(DBDocument.relevance_score.desc().nullslast())
    result = await session.execute(stmt)
    db_docs = list(result.scalars().all())

    # Fetch run metadata
    run_stmt = select(PipelineRun).where(PipelineRun.run_id == run_id)
    run_result = await session.execute(run_stmt)
    run_record = run_result.scalar_one_or_none()

    # Convert DB documents to pipeline Document objects for ExcelExporter
    from newsradar_api.domain.model.pipeline_models import Document as PipelineDoc

    docs_for_export: list[PipelineDoc] = []
    for d in db_docs:
        docs_for_export.append(PipelineDoc(
            run_id=d.run_id,
            source_id=d.source_id,
            title=d.title,
            url=d.url,
            text=d.text or "",
            excerpt=d.excerpt or "",
            hash=d.hash,
            fetch_method=d.fetch_method or "http",
            fetched_at=d.fetched_at.isoformat() if d.fetched_at else datetime.utcnow().isoformat(),
            published_at=d.published_at.isoformat() if d.published_at else None,
            category=d.category,
            severity=d.severity,
            relevance_score=d.relevance_score,
        ))

    # Build metadata
    params = run_record.params_json if run_record else {}
    metadata = {
        "run_id": run_id,
        "fecha_ejecución": (
            run_record.started_at.isoformat() if run_record and run_record.started_at
            else datetime.utcnow().isoformat()
        ),
        "empresa_o_términos": params.get("company") or params.get("terms") or "",
        "rango_fechas": f"{params.get('date_from', '')} — {params.get('date_to', '')}",
        "total_documentos": len(docs_for_export),
        "total_clasificados": sum(1 for d in docs_for_export if d.category),
    }

    # Generate Excel
    from newsradar_api.domain.usecase.excel_exporter import ExcelExporter

    exporter = ExcelExporter()
    file_name = f"{run_id}_export.xlsx"
    out_path = EXPORT_DIR / file_name
    exporter.export(docs_for_export, out_path, metadata=metadata)

    session.add(
        ExportAudit(
            export_kind="excel",
            file_name=file_name,
            file_path=str(out_path),
            status="created",
            row_count=len(docs_for_export),
            metadata_json={
                "run_id": run_id,
                "filters": request.filters or {},
            },
        )
    )
    await session.commit()

    return {
        "file_url": f"/api/export/download/{file_name}",
        "file_name": file_name,
        "total_rows": len(docs_for_export),
    }


@router.get("/download/{file_name}")
async def download_export(file_name: str) -> FileResponse:
    """Download a previously generated Excel export."""
    file_path = EXPORT_DIR / file_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Export file not found")

    return FileResponse(
        path=str(file_path),
        filename=file_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
