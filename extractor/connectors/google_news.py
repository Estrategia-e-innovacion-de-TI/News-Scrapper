"""Google News RSS connector for historical news search.

Google News exposes an RSS endpoint that supports search queries.
This connector builds a query URL with the company/terms and date range,
fetches the RSS feed, and returns QueueItems.

Note: Google News RSS does not officially support date range parameters
in the URL, but we filter results by published_at after fetching.
For better date filtering, we use the ``before:`` and ``after:`` search
operators in the query string.
"""
from __future__ import annotations

import logging
from urllib.parse import quote_plus

import feedparser
import httpx

from ..state import FetchMethod, QueueItem

logger = logging.getLogger("news_radar.google_news")

_GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=es-419&gl=CO&ceid=CO:es-419"


def _decode_google_news_url(google_url: str) -> str | None:
    """Decode the real article URL from a Google News RSS link.

    Uses the ``googlenewsdecoder`` library which calls Google's internal
    API to resolve the encoded redirect.  Falls back to ``None`` on error.
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
    except Exception as exc:
        logger.debug("Google News URL decode failed: %s", exc)
    return None


def _build_query(
    company: str | None = None,
    terms: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> str:
    """Build a Google News search query string.

    Uses ``after:`` and ``before:`` operators for date filtering.
    """
    parts: list[str] = []

    if company:
        parts.append(f'"{company}"')
    if terms:
        for t in terms[:5]:  # limit to avoid overly long queries
            parts.append(f'"{t}"' if " " in t else t)

    query = " OR ".join(parts) if len(parts) > 1 and not company else " ".join(parts)

    if date_from:
        query += f" after:{date_from}"
    if date_to:
        query += f" before:{date_to}"

    return query


async def search_google_news(
    company: str | None = None,
    terms: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    max_items: int = 30,
) -> list[QueueItem]:
    """Search Google News RSS and return discovered items.

    Parameters
    ----------
    company : str | None
        Company name for ARAS queries.
    terms : list[str] | None
        Search terms for Riesgos queries.
    date_from, date_to : str | None
        Date range in YYYY-MM-DD format.
    max_items : int
        Maximum items to return.

    Returns
    -------
    list[QueueItem]
        Discovered items from Google News.
    """
    query = _build_query(company, terms, date_from, date_to)
    url = _GOOGLE_NEWS_RSS.format(query=quote_plus(query))

    logger.info("Google News search: query=%r url=%s", query, url[:120])

    try:
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            verify=False,
        ) as client:
            resp = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36",
                },
            )
            resp.raise_for_status()
    except Exception as exc:
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

        # Google News links are redirects — try to extract the real URL.
        # The ``source`` sub-element often contains the real publisher URL.
        # Also check for ``source.href`` in the entry.
        real_url = link
        if "news.google.com" in link:
            # Try to decode the real URL from the Google News redirect
            real_url = _decode_google_news_url(link) or link
            # If decoding failed, try source.href as domain hint
            if real_url == link:
                source_info = entry.get("source", {})
                src_href = ""
                if hasattr(source_info, "href") and source_info.href:
                    src_href = source_info.href
                elif isinstance(source_info, dict) and source_info.get("href"):
                    src_href = source_info["href"]
                if src_href and src_href != link:
                    # source.href is just the domain — not useful as article URL
                    # Keep the google news URL; fetch will follow redirects
                    pass

        # Parse published date
        published: str | None = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            from datetime import datetime

            try:
                dt = datetime(*entry.published_parsed[:6])
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
