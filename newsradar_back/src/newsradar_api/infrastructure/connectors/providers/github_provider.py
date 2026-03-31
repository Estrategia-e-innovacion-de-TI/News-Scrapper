"""GitHub search provider via REST API.

Ported from news_radar_mvp/extractor/search/providers/github.py.

Validates: Requirements 18.1-18.5
"""
from __future__ import annotations

import logging
import os
from urllib.parse import quote_plus

import httpx

from ..search_models import SearchCandidate

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com/search/repositories"


async def search_github(
    term: str,
    max_results: int = 20,
    since_days: int = 90,
    timeout: int = 30,
) -> list[SearchCandidate]:
    """Search GitHub repositories matching *term*.

    Uses ``GITHUB_TOKEN`` env var for authenticated requests (higher
    rate limits).
    """
    token = os.environ.get("GITHUB_TOKEN")

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "NewsRadarBack/0.1",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    query = quote_plus(term)
    url = f"{GITHUB_API}?q={query}&sort=updated&order=desc&per_page={max_results}"

    logger.info("Searching GitHub: '%s' (max %d)", term, max_results)

    try:
        async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

        data = resp.json()
        items = data.get("items", [])
        candidates: list[SearchCandidate] = []

        for item in items:
            candidates.append(
                SearchCandidate(
                    mode="repos",
                    term=term,
                    title=item.get("full_name", ""),
                    url=item.get("html_url", ""),
                    snippet=item.get("description", "") or "",
                    published_at=item.get("created_at"),
                    source_provider="github",
                    extra={
                        "stars": item.get("stargazers_count", 0),
                        "language": item.get("language", ""),
                        "updated_at": item.get("updated_at", ""),
                        "forks": item.get("forks_count", 0),
                        "topics": item.get("topics", []),
                    },
                )
            )

        logger.info("GitHub: found %d repos for '%s'", len(candidates), term)
        return candidates

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            logger.warning("GitHub rate limit hit. Set GITHUB_TOKEN env var.")
        else:
            logger.error("GitHub search failed for '%s': %s", term, e)
        return []
    except Exception as e:
        logger.error("GitHub search failed for '%s': %s", term, e)
        return []
