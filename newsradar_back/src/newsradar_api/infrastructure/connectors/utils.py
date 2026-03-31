"""Shared utility functions for connectors.

Ported from ``news_radar_mvp/extractor/utils.py``.
Provides rate limiting, date parsing, URL normalization, and article URL
heuristics used by RSS, scrape, and Google News connectors.
"""
from __future__ import annotations

import asyncio
import re
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, urlunparse

from dateutil import parser as date_parser


# ── Rate Limiter ──────────────────────────────────────────────────────


class RateLimiter:
    """Simple per-source async rate limiter."""

    def __init__(self) -> None:
        self._last_request: dict[str, float] = {}

    async def wait(self, source_id: str, rps: float = 1.0) -> None:
        """Wait if needed to respect *rps* for *source_id*."""
        if rps <= 0:
            return
        min_interval = 1.0 / rps
        now = time.monotonic()
        last = self._last_request.get(source_id, 0)
        elapsed = now - last
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request[source_id] = time.monotonic()


rate_limiter = RateLimiter()


# ── Date helpers ──────────────────────────────────────────────────────


def parse_date(date_str: str | None) -> str | None:
    """Parse a date string to ISO-8601 format, or *None* on failure."""
    if not date_str:
        return None
    try:
        dt = date_parser.parse(date_str, fuzzy=True)
        return dt.isoformat()
    except (ValueError, TypeError):
        return None


def is_within_days(date_str: str | None, days: int) -> bool:
    """Return *True* if *date_str* is within *days* from now.

    If *date_str* is ``None`` or unparseable the entry is included
    (conservative — don't discard items we can't date).
    """
    if not date_str or days <= 0:
        return True
    try:
        dt = date_parser.parse(date_str)
        cutoff = datetime.now(dt.tzinfo) - timedelta(days=days)
        return dt >= cutoff
    except (ValueError, TypeError):
        return True


# ── URL helpers ───────────────────────────────────────────────────────


def normalize_url(url: str, base_url: str | None = None) -> str:
    """Normalize *url* for deduplication.

    Strips ``www.``, trailing slashes, and fragments.
    """
    if not url:
        return ""
    if base_url and not url.startswith(("http://", "https://")):
        url = urljoin(base_url, url)
    parsed = urlparse(url)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((scheme, netloc, path, "", "", ""))


def is_article_url(url: str, base_url: str = "") -> bool:
    """Heuristic: does *url* look like a news article?"""
    if not url:
        return False
    parsed = urlparse(url)
    path = parsed.path.lower()

    skip_patterns = [
        "/tag/", "/tags/", "/category/", "/categories/",
        "/author/", "/authors/", "/page/", "/search",
        "/login", "/register", "/subscribe", "/contact",
        "/about", "/privacy", "/terms", "/rss", "/feed",
        ".xml", ".json", ".pdf", ".jpg", ".png", ".gif",
    ]
    if any(p in path for p in skip_patterns):
        return False

    article_patterns = [
        r"/\d{4}/\d{2}/",
        r"/\d{4}-\d{2}-\d{2}",
        r"/news/", r"/noticias/", r"/article/", r"/articulo/",
        r"/post/", r"/blog/", r"/story/", r"/noticia/",
    ]
    if any(re.search(p, path) for p in article_patterns):
        return True

    # Slug-like path (words separated by hyphens)
    if re.search(r"/[\w]+-[\w]+-[\w]+", path):
        return True

    # Reasonable depth
    segments = [s for s in path.split("/") if s]
    if len(segments) >= 2:
        return True

    return False
