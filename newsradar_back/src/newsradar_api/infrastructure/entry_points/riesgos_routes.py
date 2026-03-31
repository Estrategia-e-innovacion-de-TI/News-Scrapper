"""Legacy alias endpoints for riesgos ad-hoc searches."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from newsradar_api.domain.model.dtos import (
    ArasSearchRequest,
    RiesgosSearchRequest,
    RiesgosSearchResponse,
)
from newsradar_api.infrastructure.driven_adapters.database import get_session
from newsradar_api.infrastructure.entry_points.aras_routes import search_aras_endpoint

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/search", response_model=RiesgosSearchResponse)
async def search_riesgos_endpoint(
    request: RiesgosSearchRequest,
    session: AsyncSession = Depends(get_session),
) -> RiesgosSearchResponse:
    logger.info(
        "POST /api/riesgos/search - terms=%s preset=%s classifier=%s",
        request.terms,
        request.terms_preset,
        request.classifier,
    )
    terms = list(request.terms)
    if request.terms_preset:
        try:
            from newsradar_api.domain.usecase.presets_loader import resolve_preset

            terms.extend(resolve_preset(request.terms_preset))
        except Exception:
            logger.warning("Risk preset resolution failed", exc_info=True)
    translated = ArasSearchRequest(
        term=None,
        terms=terms,
        risk_category=request.terms_preset.replace("_", " ").title() if request.terms_preset else None,
        date_from=request.date_from,
        date_to=request.date_to,
        classifier=request.classifier,
    )
    response = await search_aras_endpoint(translated, session)
    return RiesgosSearchResponse(
        run_id=response.run_id,
        search_id=response.search_id,
        audit_id=response.audit_id,
        export_id=response.export_id,
        total_documents=response.total_documents,
        total_classified=response.total_classified,
        results=response.results,
        excel_url=response.excel_url,
    )
