"""MCP tool definitions for the News Radar pipeline.

Each tool exposes a pipeline capability as an MCP-callable function.
Tools are registered at server startup and invoked by MCP clients
(newsradar_aiagent, newsradar_back, or external consumers).
"""
from __future__ import annotations

import logging
from typing import Any

from newsradar_server.domain.usecase.aras_adhoc import ArasAdhocUseCase
from newsradar_server.domain.usecase.riesgos_adhoc import RiesgosAdhocUseCase
from newsradar_server.domain.usecase.vigilancia_historical import VigilanciaHistoricalUseCase
from newsradar_server.domain.usecase.vigilancia_weekly import VigilanciaWeeklyUseCase
from newsradar_server.infrastructure.driven_adapters.clustering import ClusterEngine
from newsradar_server.infrastructure.driven_adapters.exporters import ExcelExporter, PowerBIExporter
from newsradar_server.infrastructure.driven_adapters.subscriptions import SubscriptionManager

logger = logging.getLogger(__name__)

# ── Shared helpers ────────────────────────────────────────────────────

# Singleton-style use case instances, initialized lazily via _get_*
_aras_use_case: ArasAdhocUseCase | None = None
_riesgos_use_case: RiesgosAdhocUseCase | None = None
_historical_use_case: VigilanciaHistoricalUseCase | None = None
_weekly_use_case: VigilanciaWeeklyUseCase | None = None


def _get_aras_use_case() -> ArasAdhocUseCase:
    """Return (or create) the ARAS ad-hoc use case with wired adapters."""
    global _aras_use_case
    if _aras_use_case is None:
        # TODO: Wire full adapter set from DI container when available
        _aras_use_case = ArasAdhocUseCase(
            excel_exporter=ExcelExporter(),
        )
    return _aras_use_case


def _get_riesgos_use_case() -> RiesgosAdhocUseCase:
    """Return (or create) the Riesgos ad-hoc use case with wired adapters."""
    global _riesgos_use_case
    if _riesgos_use_case is None:
        # TODO: Wire full adapter set from DI container when available
        _riesgos_use_case = RiesgosAdhocUseCase(
            excel_exporter=ExcelExporter(),
        )
    return _riesgos_use_case


def _get_historical_use_case() -> VigilanciaHistoricalUseCase:
    """Return (or create) the vigilancia historical use case with wired adapters."""
    global _historical_use_case
    if _historical_use_case is None:
        # TODO: Wire full adapter set from DI container when available
        _historical_use_case = VigilanciaHistoricalUseCase(
            cluster_engine=ClusterEngine(),
            powerbi_exporter=PowerBIExporter(),
        )
    return _historical_use_case


def _get_weekly_use_case() -> VigilanciaWeeklyUseCase:
    """Return (or create) the vigilancia weekly use case with wired adapters."""
    global _weekly_use_case
    if _weekly_use_case is None:
        _weekly_use_case = VigilanciaWeeklyUseCase(
            subscription_manager=SubscriptionManager(),
        )
    return _weekly_use_case


# ── MCP Tool Definitions ─────────────────────────────────────────────


def tool_aras_search(
    *,
    company: str | None = None,
    nit: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    classifier_mode: str = "rules",
) -> dict[str, Any]:
    """MCP Tool: Execute an ARAS ad-hoc search.

    Runs the full ARAS pipeline: resolve NIT → search → classify →
    severity → evidence → export Excel.

    Returns dict with results summary and Excel file path.
    """
    logger.info(
        "MCP tool_aras_search invoked: company=%s, nit=%s, classifier=%s",
        company, nit, classifier_mode,
    )
    use_case = _get_aras_use_case()
    return use_case.execute(
        company=company,
        nit=nit,
        date_from=date_from,
        date_to=date_to,
        classifier_mode=classifier_mode,
    )


def tool_riesgos_search(
    *,
    terms: list[str] | None = None,
    terms_preset: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    classifier_mode: str = "rules",
) -> dict[str, Any]:
    """MCP Tool: Execute a Riesgos Emergentes ad-hoc search.

    Runs the full Riesgos pipeline: resolve terms/preset → search →
    classify → severity → evidence → export Excel.

    Returns dict with results summary and Excel file path.
    """
    logger.info(
        "MCP tool_riesgos_search invoked: terms=%s, preset=%s, classifier=%s",
        terms, terms_preset, classifier_mode,
    )
    use_case = _get_riesgos_use_case()
    return use_case.execute(
        terms=terms,
        terms_preset=terms_preset,
        date_from=date_from,
        date_to=date_to,
        classifier_mode=classifier_mode,
    )


def tool_vigilancia_weekly() -> dict[str, Any]:
    """MCP Tool: Execute the weekly vigilancia pipeline.

    Fetches news for all query groups, scores by relevance,
    selects top-10 per group, filters by subscriber subscriptions.

    Returns dict with per-subscriber result sets.
    """
    logger.info("MCP tool_vigilancia_weekly invoked")
    use_case = _get_weekly_use_case()
    return use_case.execute()


def tool_vigilancia_historical(
    *, modes: list[str] | None = None
) -> dict[str, Any]:
    """MCP Tool: Execute historical vigilancia analysis.

    Clusters papers/repos/patents by TF-IDF similarity,
    computes trend timelines and hype indicators,
    exports Power BI JSON.

    Returns dict with clustering results and Power BI JSON path.
    """
    logger.info("MCP tool_vigilancia_historical invoked: modes=%s", modes)
    use_case = _get_historical_use_case()
    return use_case.execute(modes=modes)


def tool_extract_news(
    *, focus: str | None = None, days: int = 7
) -> dict[str, Any]:
    """MCP Tool: Run the full news extraction pipeline.

    Orchestrates: load catalog → select sources → discover →
    fetch → classify/score → persist.

    Returns dict with run metrics.
    """
    # TODO: Wire to extract_news use case via DI container
    raise NotImplementedError("TODO: wire MCP tool to extract_news use case")
