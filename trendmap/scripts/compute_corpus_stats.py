"""Paso 1 — Compute corpus statistics from JSONL sources.

Counts articles/papers, extracts date range, saves to data/corpus_stats.json.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

DATE_FIELDS = ["published_at", "published", "date", "created_at", "timestamp", "fetched_at"]


def _parse_date(val: str | None) -> datetime | None:
    if not val:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            return dt.replace(tzinfo=None)  # normalize to naive
        except (ValueError, TypeError):
            continue
    return None


def _extract_date(doc: dict) -> datetime | None:
    for field in DATE_FIELDS:
        d = _parse_date(doc.get(field))
        if d:
            return d
    return None


def count_jsonl(path: Path) -> tuple[int, list[datetime]]:
    count = 0
    dates: list[datetime] = []
    warnings: list[str] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    doc = json.loads(line)
                    count += 1
                    d = _extract_date(doc)
                    if d:
                        dates.append(d)
                except json.JSONDecodeError:
                    warnings.append(f"Line {i+1} invalid JSON")
    except FileNotFoundError:
        pass
    return count, dates


def fallback_from_powerbi(path: Path) -> tuple[int, list[datetime]]:
    """Extract counts and dates from powerbi_data.json as fallback."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        dates = []
        count = 0
        for cluster in data.get("clusters", []):
            for item in cluster.get("items", []):
                count += 1
                d = _extract_date(item)
                if d:
                    dates.append(d)
        for item in data.get("top_items", []):
            d = _extract_date(item)
            if d:
                dates.append(d)
        return count, dates
    except Exception:
        return 0, []


def main():
    config_path = Path(__file__).parent.parent / "config" / "trendmap.yml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    paths = config.get("paths", {})
    base = Path(__file__).parent.parent.parent  # news_radar_mvp/

    articles_path = base / paths.get("articles", "out/articles.jsonl")
    papers_path = base / paths.get("papers", "out/articles_papers.jsonl")
    powerbi_path = base / paths.get("powerbi", "out/analysis_combined/powerbi_data.json")
    output_dir = base / paths.get("output_dir", "trendmap/data")
    output_dir.mkdir(parents=True, exist_ok=True)

    warnings_list: list[str] = []
    computed_from: list[str] = []

    # Count from JSONL files
    news_count, news_dates = count_jsonl(articles_path)
    papers_count, papers_dates = count_jsonl(papers_path)

    if news_count > 0:
        computed_from.append(str(articles_path.name))
        logger.info("News: %d articles, %d with dates", news_count, len(news_dates))
    else:
        warnings_list.append(f"{articles_path.name} not found or empty")

    if papers_count > 0:
        computed_from.append(str(papers_path.name))
        logger.info("Papers: %d articles, %d with dates", papers_count, len(papers_dates))
    else:
        warnings_list.append(f"{papers_path.name} not found or empty")

    all_dates = news_dates + papers_dates

    # Filter out dates before 2024 (stale/static pages)
    all_dates = [d for d in all_dates if d.year >= 2024]

    # Fallback to powerbi if no JSONL
    if not all_dates:
        fb_count, fb_dates = fallback_from_powerbi(powerbi_path)
        if fb_dates:
            all_dates = fb_dates
            computed_from.append("powerbi_data.json (fallback)")
            warnings_list.append("Dates derived from powerbi_data.json")
            logger.info("Fallback: %d items from powerbi_data.json", fb_count)

    min_date = min(all_dates).replace(tzinfo=None).isoformat() if all_dates else None
    max_date = max(all_dates).replace(tzinfo=None).isoformat() if all_dates else None

    stats = {
        "news_count": news_count,
        "papers_count": papers_count,
        "total_count": news_count + papers_count,
        "min_date": min_date,
        "max_date": max_date,
        "computed_from": computed_from,
        "warnings": warnings_list,
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
    }

    out_path = output_dir / "corpus_stats.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    logger.info("Saved: %s", out_path)
    logger.info("News=%d, Papers=%d, Range=%s → %s", news_count, papers_count, min_date, max_date)
    return 0


if __name__ == "__main__":
    sys.exit(main())
