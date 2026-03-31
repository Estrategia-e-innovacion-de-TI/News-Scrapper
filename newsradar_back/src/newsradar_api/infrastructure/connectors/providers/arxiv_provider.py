"""ArXiv search provider via RSS/Atom API.

Ported from news_radar_mvp/extractor/search/providers/arxiv.py.

Validates: Requirements 18.1-18.5
"""
from __future__ import annotations

import logging
from urllib.parse import quote_plus

import feedparser
import httpx

from ..search_models import SearchCandidate

logger = logging.getLogger(__name__)

ARXIV_API = "http://export.arxiv.org/api/query"


async def search_arxiv(
    term: str,
    max_results: int = 20,
    since_days: int = 30,
    timeout: int = 30,
) -> list[SearchCandidate]:
    """Search ArXiv for papers matching *term*.

    Parameters
    ----------
    term
        Free-text search query.
    max_results
        Maximum number of results to return.
    since_days
        Not directly supported by ArXiv API; results are sorted by
        submission date descending so recent papers come first.
    timeout
        HTTP request timeout in seconds.
    """
    query = quote_plus(term)
    url = (
        f"{ARXIV_API}?search_query=all:{query}"
        f"&start=0&max_results={max_results}"
        f"&sortBy=submittedDate&sortOrder=descending"
    )

    logger.info("Searching ArXiv: '%s' (max %d)", term, max_results)

    try:
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=True, verify=False,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        feed = feedparser.parse(resp.text)
        candidates: list[SearchCandidate] = []

        for entry in feed.entries:
            title = entry.get("title", "").replace("\n", " ").strip()
            summary = entry.get("summary", "").replace("\n", " ").strip()
            link = entry.get("link", "")
            published = entry.get("published", "")
            authors = ", ".join(
                a.get("name", "") for a in entry.get("authors", [])
            )

            candidates.append(
                SearchCandidate(
                    mode="papers",
                    term=term,
                    title=title,
                    url=link,
                    snippet=summary[:500],
                    published_at=published,
                    source_provider="arxiv",
                    extra={"authors": authors},
                )
            )

        logger.info("ArXiv: found %d papers for '%s'", len(candidates), term)
        return candidates

    except Exception as e:
        logger.error("ArXiv search failed for '%s': %s", term, e)
        return []
