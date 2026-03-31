"""Google News RSS connector for historical news search.

Ported from ``news_radar_mvp/extractor/connectors/google_news.py``.
Builds a search query with ``after:``/``before:`` operators, fetches the
Google News RSS endpoint, and decodes redirect URLs via
``googlenewsdecoder``.

Validates: Requirements 8.1-8.4
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus

import feedparser
import httpx

from newsradar_api.domain.model.pipeline_models import FetchMethod, QueueItem

logger = logging.getLogger(__name__)

_GOOGLE_NEWS_RSS = (
    "https://news.google.com/rss/search"
    "?q={query}&hl=es-419&gl=CO&ceid=CO:es-419"
)

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# ── Internal helpers ──────────────────────────────────────────────────


def _decode_google_news_url(google_url: str) -> str | None:
    """Decode the real article URL from a Google News redirect link.

    Uses ``googlenewsdecoder`` which calls Google's internal API to
    resolve the encoded redirect.  Returns *None* on any error.

    Validates: Requirement 8.3
    """
    try:
        # Patch requests to skip SSL verification (corporate proxies)
        import requests as _req

        _orig_send = _req.Session.send

        def _patched_send(self: Any, *args: Any, **kwargs: Any) -> Any:
            kwargs["verify"] = False
            return _orig_send(self, *args, **kwargs)

        _req.Session.send = _patched_send  # type: ignore[assignment]

        from googlenewsdecoder import new_decoderv1

        result = new_decoderv1(google_url)
        _req.Session.send = _orig_send  # restore

        if result and result.get("decoded_url"):
            return result["decoded_url"]
    except Exception as exc:  # noqa: BLE001
        logger.debug("Google News URL decode failed: %s", exc)
    return None


def _build_query(
    company: str | None = None,
    terms: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> str:
    """Build a Google News search query string.

    Uses ``after:``/``before:`` operators for date filtering and quotes
    for exact phrase matching.

    Validates: Requirement 8.1
    """
    parts: list[str] = []

    if company:
        parts.append(f'"{company}"')
    if terms:
        for t in terms[:5]:  # limit to avoid overly long queries
            parts.append(f'"{t}"' if " " in t else t)

    # Use OR when multiple independent terms, plain join when company present
    query = (
        " OR ".join(parts)
        if len(parts) > 1 and not company
        else " ".join(parts)
    )

    if date_from:
        query += f" after:{date_from}"
    if date_to:
        query += f" before:{date_to}"

    return query


# ── Public API ────────────────────────────────────────────────────────


async def search(
    company: str | None = None,
    terms: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    max_items: int = 30,
) -> list[QueueItem]:
    """Search Google News RSS and return discovered items.

    Parameters
    ----------
    company:
        Company name for ARAS queries.
    terms:
        Search terms for Riesgos queries.
    date_from, date_to:
        Date range in ``YYYY-MM-DD`` format.
    max_items:
        Maximum items to return (default 30).

    Returns
    -------
    list[QueueItem]
        Discovered items from Google News.

    Validates: Requirements 8.1-8.4
    """
    query = _build_query(company, terms, date_from, date_to)
    url = _GOOGLE_NEWS_RSS.format(query=quote_plus(query))

    logger.info("Google News search: query=%r url=%s", query, url[:120])

    # Fetch the RSS feed (Req 8.2)
    try:
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            verify=False,
        ) as client:
            resp = await client.get(url, headers={"User-Agent": _USER_AGENT})
            resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        logger.error("Google News fetch failed: %s", exc)
        return []

    feed = feedparser.parse(resp.text)
    if not feed.entries:
        logger.warning("Google News returned 0 entries for query=%r", query)
        return []

    items: list[QueueItem] = []
    for entry in feed.entries[:max_items]:
        link = entry.get("link", "")
        if not link:
            continue

        # Decode redirect URLs (Req 8.3)
        real_url = link
        if "news.google.com" in link:
            decoded = _decode_google_news_url(link)
            if decoded:
                real_url = decoded

        # Parse published date
        published: str | None = None
        pp = getattr(entry, "published_parsed", None) or entry.get(
            "published_parsed"
        )
        if pp:
            try:
                dt = datetime(*pp[:6])
                published = dt.isoformat()
            except (TypeError, ValueError):
                pass

        items.append(
            QueueItem(
                source_id="google_news",
                url=real_url,
                source_url=url,
                fetch_method=FetchMethod.HTTP,
                title=entry.get("title", ""),
                published_at=published,
            )
        )

    logger.info("Google News: %d items found for query=%r", len(items), query[:60])
    return items
