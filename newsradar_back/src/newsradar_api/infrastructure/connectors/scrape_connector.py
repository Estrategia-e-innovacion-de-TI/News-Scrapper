"""Web scraping connector for listing pages.

Ported from ``news_radar_mvp/extractor/connectors/scrape.py``.
Discovers :class:`QueueItem` objects by scraping listing pages defined
in a :class:`SourceConfig`, using either a CSS selector or heuristics
to identify article links.

Validates: Requirements 7.1-7.5
"""
from __future__ import annotations

import logging
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from newsradar_api.domain.model.pipeline_models import (
    FetchMethod,
    QueueItem,
    SourceConfig,
)
from .utils import is_article_url, normalize_url, rate_limiter

logger = logging.getLogger(__name__)

_DEFAULT_HEADERS = {
    "User-Agent": "NewsRadarAPI/1.0 (+contact: security-research@yourorg.com)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es,en;q=0.9",
}


# ── Internal helpers ──────────────────────────────────────────────────


async def _fetch_html(
    url: str,
    timeout: int = 25,
    headers: dict[str, str] | None = None,
) -> tuple[str | None, int]:
    """Fetch HTML from *url*. Returns ``(html, status_code)``.

    Non-HTTP errors use conventional codes: 0 = timeout/connection,
    -1 = TLS, -2 = too many redirects.
    """
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            verify=False,
        ) as client:
            response = await client.get(url, headers=headers or _DEFAULT_HEADERS)
            return response.text, response.status_code
    except httpx.HTTPStatusError as exc:
        logger.error("HTTP error fetching %s: %s", url, exc.response.status_code)
        return None, exc.response.status_code
    except httpx.TimeoutException:
        logger.error("Timeout fetching %s", url)
        return None, 0
    except httpx.ConnectError as exc:
        err_str = str(exc).lower()
        if any(kw in err_str for kw in ("ssl", "tls", "certificate")):
            logger.error("TLS error fetching %s: %s", url, exc)
            return None, -1
        logger.error("Connection error fetching %s: %s", url, exc)
        return None, 0
    except httpx.TooManyRedirects:
        logger.error("Too many redirects for %s", url)
        return None, -2
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error fetching %s: %s", url, exc)
        return None, 0


def _extract_links_by_selector(
    html: str,
    selector: str,
    base_url: str,
) -> list[str]:
    """Extract links using a CSS selector (Req 7.2)."""
    soup = BeautifulSoup(html, "lxml")
    links: list[str] = []
    for element in soup.select(selector):
        href = element.get("href")
        if href:
            links.append(urljoin(base_url, href))
    return links


def _extract_links_heuristic(
    html: str,
    base_url: str,
    max_links: int = 50,
) -> list[str]:
    """Extract article links using heuristics (Req 7.3).

    Filters to same domain, article-like URL patterns, up to
    *max_links* results.
    """
    soup = BeautifulSoup(html, "lxml")
    base_domain = urlparse(base_url).netloc.replace("www.", "")

    links: list[str] = []
    seen: set[str] = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag.get("href", "")
        if not href:
            continue

        full_url = urljoin(base_url, href)
        normalized = normalize_url(full_url)

        if normalized in seen:
            continue
        seen.add(normalized)

        # Same domain check
        link_domain = urlparse(full_url).netloc.replace("www.", "")
        if base_domain not in link_domain:
            continue

        if is_article_url(full_url, base_url):
            links.append(full_url)
            if len(links) >= max_links:
                break

    return links


# ── Public API ────────────────────────────────────────────────────────


async def discover(
    source: SourceConfig,
    max_items: int = 20,
) -> list[QueueItem]:
    """Discover items from listing pages of *source*.

    Parameters
    ----------
    source:
        Catalog source with ``listing_urls`` populated.
    max_items:
        Maximum number of items to return.

    Returns
    -------
    list[QueueItem]
        Discovered queue items ready for fetch.

    Validates: Requirements 7.1-7.5
    """
    items: list[QueueItem] = []
    seen_urls: set[str] = set()

    for listing_url in source.listing_urls:
        await rate_limiter.wait(source.source_id, source.rate_limit_rps)

        logger.info("[%s] Scraping listing: %s", source.source_id, listing_url)

        html, status = await _fetch_html(listing_url, source.timeout_seconds)

        # Req 7.5 — warn on 403 and continue
        if status == 403:
            logger.warning("[%s] Blocked (403): %s", source.source_id, listing_url)
            continue

        if not html:
            logger.warning("[%s] Failed to fetch: %s", source.source_id, listing_url)
            continue

        # Choose extraction strategy (Req 7.2 vs 7.3)
        selector = source.selectors.get("article_link_css")
        base = source.base_url or listing_url

        if selector:
            links = _extract_links_by_selector(html, selector, base)
        else:
            links = _extract_links_heuristic(html, base)

        logger.debug("[%s] Found %d links", source.source_id, len(links))

        for url in links:
            # Req 7.4 — normalize and deduplicate
            normalized = normalize_url(url)
            if normalized in seen_urls:
                continue
            seen_urls.add(normalized)

            items.append(
                QueueItem(
                    source_id=source.source_id,
                    url=url,
                    source_url=listing_url,
                    fetch_method=(
                        FetchMethod.PLAYWRIGHT
                        if source.requires_playwright
                        else FetchMethod.HTTP
                    ),
                    requires_playwright=source.requires_playwright,
                )
            )

            if len(items) >= max_items:
                break

        if len(items) >= max_items:
            break

    logger.info("[%s] Discovered %d scrape items", source.source_id, len(items))
    return items
