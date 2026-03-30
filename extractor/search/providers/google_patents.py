"""Google Patents search provider via Google SERP with site: filter."""
from __future__ import annotations

import logging
import re
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

from ..models import SearchCandidate

logger = logging.getLogger("news_radar.search.patents")

# Google Patents is a JS SPA, so we search via Google with site: filter
GOOGLE_SEARCH = "https://www.google.com/search"


async def search_google_patents(
    term: str,
    max_results: int = 20,
    timeout: int = 30,
) -> list[SearchCandidate]:
    """Search Google Patents via Google SERP with site:patents.google.com."""
    query = f"site:patents.google.com {term}"
    encoded = quote_plus(query)
    url = f"{GOOGLE_SEARCH}?q={encoded}&num={min(max_results, 10)}"

    logger.info(f"Searching Google Patents (via SERP): '{term}' (max {max_results})")

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            verify=False,
        ) as client:
            resp = await client.get(url, headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            })
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        candidates = []

        # Parse Google SERP results
        for g in soup.select("div.g, div[data-sokoban-container]"):
            a = g.find("a", href=True)
            if not a:
                continue
            href = a.get("href", "")
            if "patents.google.com" not in href:
                continue

            title_el = a.find("h3") or a
            title = title_el.get_text(strip=True) if title_el else ""

            # Snippet
            snippet_el = (
                g.find("div", class_="VwiC3b")
                or g.find("span", class_="aCOpRe")
                or g.find("div", class_="IsZvec")
            )
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""

            if title:
                candidates.append(SearchCandidate(
                    mode="patents",
                    term=term,
                    title=title,
                    url=href,
                    snippet=snippet[:500],
                    source_provider="google_patents",
                ))

                if len(candidates) >= max_results:
                    break

        # Fallback: any link to patents.google.com/patent/
        if not candidates:
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                if "patents.google.com/patent/" in href:
                    title = a.get_text(strip=True)
                    if title and len(title) > 5:
                        candidates.append(SearchCandidate(
                            mode="patents",
                            term=term,
                            title=title,
                            url=href,
                            snippet="",
                            source_provider="google_patents",
                        ))
                        if len(candidates) >= max_results:
                            break

        if not candidates:
            logger.warning(
                f"Google Patents: 0 results for '{term}'. "
                "Google SERP may require JS rendering or CAPTCHA. "
                "Consider using SerpAPI or Playwright for reliable patent search."
            )
        else:
            logger.info(f"Google Patents: found {len(candidates)} patents for '{term}'")
        return candidates

    except Exception as e:
        logger.error(f"Google Patents search failed for '{term}': {e}")
        return []
