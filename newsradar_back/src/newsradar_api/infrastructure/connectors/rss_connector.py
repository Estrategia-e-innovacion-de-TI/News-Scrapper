"""RSS / Atom feed connector.

Ported from ``news_radar_mvp/extractor/connectors/rss.py``.
Discovers :class:`QueueItem` objects from RSS/Atom feeds listed in a
:class:`SourceConfig`, filtering by publication date and respecting
per-source rate limits.

Validates: Requirements 6.1-6.5
"""
from __future__ import annotations

import logging
from datetime import datetime

import feedparser
import httpx

from newsradar_api.domain.model.pipeline_models import (
    FetchMethod,
    QueueItem,
    SourceConfig,
)
from .utils import is_within_days, parse_date, rate_limiter

logger = logging.getLogger(__name__)

_USER_AGENT = "NewsRadarAPI/1.0 (+contact: security-research@yourorg.com)"
_ACCEPT = (
    "application/rss+xml, application/atom+xml, "
    "application/xml, text/xml"
)


# ── Internal helpers ──────────────────────────────────────────────────


async def _fetch_feed(
    url: str,
    timeout: int = 25,
) -> feedparser.FeedParserDict | None:
    """Fetch and parse an RSS/Atom feed, returning *None* on error."""
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            verify=False,
        ) as client:
            response = await client.get(
                url,
                headers={"User-Agent": _USER_AGENT, "Accept": _ACCEPT},
            )
            response.raise_for_status()

            feed = feedparser.parse(response.text)
            if feed.bozo and not feed.entries:
                logger.warning("Feed parse error for %s: %s", url, feed.bozo_exception)
                return None
            return feed

    except httpx.HTTPStatusError as exc:
        logger.error("HTTP error fetching feed %s: %s", url, exc.response.status_code)
    except httpx.RequestError as exc:
        logger.error("Request error fetching feed %s: %s", url, exc)
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error fetching feed %s: %s", url, exc)
    return None


def _parse_entry_date(entry: dict) -> str | None:
    """Extract and parse the publication date from a feed entry.

    Checks ``published``, ``updated``, ``created``, ``pubDate`` string
    fields first, then falls back to ``published_parsed`` (time.struct).

    Validates: Requirement 6.2
    """
    for field in ("published", "updated", "created", "pubDate"):
        raw = entry.get(field)
        if raw:
            parsed = parse_date(raw)
            if parsed:
                return parsed

    # Fallback: feedparser's pre-parsed struct_time
    pp = getattr(entry, "published_parsed", None) or entry.get("published_parsed")
    if pp:
        try:
            dt = datetime(*pp[:6])
            return dt.isoformat()
        except (TypeError, ValueError):
            pass

    return None


# ── Public API ────────────────────────────────────────────────────────


async def discover(
    source: SourceConfig,
    days: int = 7,
    max_items: int = 20,
) -> list[QueueItem]:
    """Discover items from the RSS feeds of *source*.

    Parameters
    ----------
    source:
        Catalog source with ``rss_urls`` populated.
    days:
        Only include entries published within this many days.
    max_items:
        Maximum number of items to return across all feeds.

    Returns
    -------
    list[QueueItem]
        Discovered queue items ready for fetch.

    Validates: Requirements 6.1-6.5
    """
    items: list[QueueItem] = []

    # Respect rate limit before starting requests (Req 6.4)
    await rate_limiter.wait(source.source_id, source.rate_limit_rps)

    for feed_url in source.rss_urls:
        logger.info("[%s] Fetching RSS: %s", source.source_id, feed_url)

        feed = await _fetch_feed(feed_url, source.timeout_seconds)
        if not feed or not feed.entries:
            logger.warning("[%s] No entries in feed: %s", source.source_id, feed_url)
            continue

        for entry in feed.entries:
            url = entry.get("link", "")
            if not url:
                continue

            # Parse and filter by date range (Req 6.2, 6.3)
            published = _parse_entry_date(entry)
            if not is_within_days(published, days):
                continue

            title = entry.get("title", "")

            items.append(
                QueueItem(
                    source_id=source.source_id,
                    url=url,
                    source_url=feed_url,
                    fetch_method=FetchMethod.RSS,
                    title=title,
                    published_at=published,
                    requires_playwright=source.requires_playwright,
                )
            )

            # Limit total items (Req 6.5)
            if len(items) >= max_items:
                break

        if len(items) >= max_items:
            break

    logger.info("[%s] Discovered %d RSS items", source.source_id, len(items))
    return items
