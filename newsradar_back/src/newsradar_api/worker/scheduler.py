"""Simple scheduler metadata for local development."""
from __future__ import annotations

DEFAULT_SCHEDULES = {
    "tech_watch_ingest": "weekly",
    "trendmap_generate": "after_relevant_tech_watch_execution",
    "risk_mapping_ingest": "weekly_news_and_bimonthly_institutional",
    "riskmap_generate": "after_relevant_risk_execution",
}
