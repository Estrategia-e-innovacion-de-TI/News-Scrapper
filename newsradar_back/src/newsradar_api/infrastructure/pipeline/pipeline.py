"""LangGraph pipeline definition for news extraction.

Defines a :class:`StateGraph` with nodes in order:
  load_catalog → select_sources → discover_items → split_lane →
  fetch_content_http → fetch_content_browser → extract_pdf →
  classify_and_score → persist_and_report

Supports all pipeline parameters including dry_run, ad-hoc modes,
deduplication by content_hash, and historical-query optimisation
(skip RSS/scrape when date_to > 3 days in the past).

Ported from ``news_radar_mvp/extractor/graph.py``.

Validates: Requirements 19.1-19.6, 16.5
"""
from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from newsradar_api.domain.model.pipeline_models import GraphState
from newsradar_api.infrastructure.pipeline.nodes import (
    classify_and_score_node,
    discover_items_node,
    extract_pdf_node,
    fetch_content_browser_node,
    fetch_content_http_node,
    load_catalog_node,
    persist_and_report_node,
    select_sources_node,
    split_lane_node,
)

logger = logging.getLogger("newsradar.pipeline")


# ── Graph builder ─────────────────────────────────────────────────────


def build_graph() -> StateGraph:
    """Build the LangGraph workflow with all pipeline nodes.

    Node order (Req 19.1):
      load_catalog → select_sources → discover_items → split_lane →
      fetch_content_http → fetch_content_browser → extract_pdf →
      classify_and_score → persist_and_report → END
    """
    workflow = StateGraph(GraphState)

    workflow.add_node("load_catalog", load_catalog_node)
    workflow.add_node("select_sources", select_sources_node)
    workflow.add_node("discover_items", discover_items_node)
    workflow.add_node("split_lane", split_lane_node)
    workflow.add_node("fetch_content_http", fetch_content_http_node)
    workflow.add_node("fetch_content_browser", fetch_content_browser_node)
    workflow.add_node("extract_pdf", extract_pdf_node)
    workflow.add_node("classify_and_score", classify_and_score_node)
    workflow.add_node("persist_and_report", persist_and_report_node)

    workflow.set_entry_point("load_catalog")
    workflow.add_edge("load_catalog", "select_sources")
    workflow.add_edge("select_sources", "discover_items")
    workflow.add_edge("discover_items", "split_lane")
    workflow.add_edge("split_lane", "fetch_content_http")
    workflow.add_edge("fetch_content_http", "fetch_content_browser")
    workflow.add_edge("fetch_content_browser", "extract_pdf")
    workflow.add_edge("extract_pdf", "classify_and_score")
    workflow.add_edge("classify_and_score", "persist_and_report")
    workflow.add_edge("persist_and_report", END)

    return workflow


def compile_graph():
    """Compile the graph for execution."""
    return build_graph().compile()


# ── Pipeline runner ───────────────────────────────────────────────────


async def run_extraction(
    run_id: str | None = None,
    catalog_path: str = "catalog.yaml",
    days: int = 7,
    max_items_per_source: int = 20,
    out_dir: str = "out",
    debug: bool = False,
    dry_run: bool = False,
    only_source: str | None = None,
    no_playwright: bool = False,
    focus: str | None = None,
    adhoc: bool = False,
    company: str | None = None,
    terms: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    topk_per_source: int = 5,
    max_candidates_total: int = 50,
    candidates_path: str | None = None,
    classifier_mode: str = "rules",
    nit: str | None = None,
    terms_preset: str | None = None,
) -> GraphState:
    """Run the extraction pipeline.

    Supports all parameters defined in Req 19.2:
      catalog_path, days, max_items_per_source, focus, adhoc, company,
      terms, date_from, date_to, classifier_mode, dry_run, nit, terms_preset.

    In dry_run mode (Req 19.3), fetch phases are skipped and the state
    is returned with the discovered queue items.

    When date_to > 3 days in the past (Req 16.5), RSS/scrape discovery
    is skipped and only Google News is used.

    Deduplication by content_hash is performed during fetch (Req 19.5).

    Returns the final :class:`GraphState` after all nodes have executed.
    """
    # Resolve NIT if provided
    if nit and not company:
        try:
            from newsradar_api.domain.usecase.nit_resolver import NITResolver

            resolver = NITResolver()
            resolved = resolver.resolve(nit)
            if resolved:
                company = resolved
                logger.info("NIT %s resolved to company: %s", nit, company)
        except Exception as exc:
            logger.warning("NIT resolution failed: %s", exc)

    # Resolve terms preset if provided
    if terms_preset and not terms:
        try:
            from newsradar_api.domain.usecase.presets_loader import PresetsLoader

            loader = PresetsLoader()
            resolved_terms = loader.resolve_preset(terms_preset)
            if resolved_terms:
                terms = resolved_terms
                logger.info("Preset '%s' resolved to terms: %s", terms_preset, terms)
        except Exception as exc:
            logger.warning("Preset resolution failed: %s", exc)

    initial_state = GraphState(
        run_id=run_id or GraphState().run_id,
        catalog_path=catalog_path,
        days=days,
        max_items_per_source=max_items_per_source,
        out_dir=out_dir,
        debug=debug,
        dry_run=dry_run,
        only_source=only_source,
        no_playwright=no_playwright,
        focus=focus,
        adhoc=adhoc,
        company=company,
        terms=terms,
        date_from=date_from,
        date_to=date_to,
        topk_per_source=topk_per_source,
        max_candidates_total=max_candidates_total,
        candidates_path=candidates_path,
        classifier_mode=classifier_mode,
        nit=nit,
        terms_preset=terms_preset,
    )

    app = compile_graph()

    logger.info("Starting extraction run %s", initial_state.run_id)
    if focus:
        logger.info("Focus: %s, adhoc=%s", focus, adhoc)

    final_state = await app.ainvoke(initial_state)

    return GraphState(**final_state)


__all__ = ["build_graph", "compile_graph", "run_extraction"]
