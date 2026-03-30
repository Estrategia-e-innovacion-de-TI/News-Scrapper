"""Metrics collection and run report generation."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .state import Document, GraphState, RunMetrics, SourceMetrics

logger = logging.getLogger("news_radar.report")


def init_source_metrics(source_id: str, requires_playwright: bool = False) -> SourceMetrics:
    """Initialize metrics for a source."""
    return SourceMetrics(
        source_id=source_id,
        requires_playwright=requires_playwright,
    )


def update_source_metrics(
    metrics: SourceMetrics,
    discovered: int = 0,
    fetched_ok: int = 0,
    text_ok: int = 0,
    dupes: int = 0,
    skipped: int = 0,
    errors: int = 0,
    error_type: str | None = None,
    text_len: int = 0,
) -> SourceMetrics:
    """Update source metrics with new values."""
    metrics.discovered += discovered
    metrics.fetched_ok += fetched_ok
    metrics.text_ok += text_ok
    metrics.dupes += dupes
    metrics.skipped += skipped
    metrics.errors += errors
    
    if error_type:
        metrics.errors_by_type[error_type] = metrics.errors_by_type.get(error_type, 0) + 1
    
    # Update average text length
    if text_len > 0 and metrics.text_ok > 0:
        total_len = metrics.avg_text_len * (metrics.text_ok - 1) + text_len
        metrics.avg_text_len = total_len / metrics.text_ok
    
    return metrics


def compute_run_metrics(state: GraphState) -> RunMetrics:
    """Compute final run metrics from state."""
    finished_at = datetime.utcnow().isoformat()
    started = datetime.fromisoformat(state.started_at)
    finished = datetime.fromisoformat(finished_at)
    duration = (finished - started).total_seconds()
    
    # Aggregate from source metrics
    total_discovered = 0
    total_fetched = 0
    total_ok = 0
    total_skipped = 0
    total_errors = 0
    total_dupes = 0
    
    for sm in state.source_metrics.values():
        total_discovered += sm.discovered
        total_fetched += sm.fetched_ok
        total_ok += sm.text_ok
        total_skipped += sm.skipped
        total_errors += sm.errors
        total_dupes += sm.dupes
    
    return RunMetrics(
        run_id=state.run_id,
        started_at=state.started_at,
        finished_at=finished_at,
        duration_seconds=round(duration, 2),
        total_sources=len(state.selected_sources),
        total_discovered=total_discovered,
        total_fetched=total_fetched,
        total_ok=total_ok,
        total_skipped=total_skipped,
        total_errors=total_errors,
        total_dupes=total_dupes,
        by_source={k: v.model_dump() for k, v in state.source_metrics.items()},
    )


def generate_report(state: GraphState) -> dict[str, Any]:
    """Generate run report dictionary."""
    metrics = compute_run_metrics(state)
    
    # Convert by_source to serializable dict
    by_source = {}
    for k, v in metrics.by_source.items():
        if isinstance(v, dict):
            by_source[k] = v
        elif hasattr(v, 'model_dump'):
            by_source[k] = v.model_dump()
        else:
            by_source[k] = dict(v)
    
    report = {
        "run_id": metrics.run_id,
        "started_at": metrics.started_at,
        "finished_at": metrics.finished_at,
        "duration_seconds": metrics.duration_seconds,
        "summary": {
            "total_sources": metrics.total_sources,
            "total_discovered": metrics.total_discovered,
            "total_fetched": metrics.total_fetched,
            "total_ok": metrics.total_ok,
            "total_skipped": metrics.total_skipped,
            "total_errors": metrics.total_errors,
            "total_dupes": metrics.total_dupes,
        },
        "by_source": by_source,
        "params": {
            "catalog_path": state.catalog_path,
            "days": state.days,
            "max_items_per_source": state.max_items_per_source,
            "dry_run": state.dry_run,
            "no_playwright": state.no_playwright,
            "only_source": state.only_source,
            "focus": state.focus,
            "adhoc": state.adhoc,
            "max_text_chars": state.max_text_chars,
        },
    }
    
    # Add adhoc summary when applicable
    if state.adhoc and state.focus:
        report["adhoc_summary"] = {
            "focus": state.focus,
            "query_type": "aras",
            "company": state.company,
            "date_from": state.date_from,
            "date_to": state.date_to,
            "topk_per_source": state.topk_per_source,
            "max_candidates_total": state.max_candidates_total,
            "match_mode": state.match_mode,
        }
    
    return report


def save_report(state: GraphState, out_dir: str | Path) -> Path:
    """Save run report to JSON file."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    report = generate_report(state)
    report_path = out_dir / "run_report.json"
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Report saved to {report_path}")
    return report_path


def save_documents_jsonl(documents: list[Document], out_dir: str | Path) -> Path:
    """Save documents to JSONL file."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    jsonl_path = out_dir / "articles.jsonl"
    
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for doc in documents:
            line = json.dumps(doc.model_dump(), ensure_ascii=False)
            f.write(line + "\n")
    
    logger.info(f"Saved {len(documents)} documents to {jsonl_path}")
    return jsonl_path
