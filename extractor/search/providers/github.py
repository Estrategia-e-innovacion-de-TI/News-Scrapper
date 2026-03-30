"""GitHub search provider via API or fallback."""
from __future__ import annotations

import logging
import os
from urllib.parse import quote_plus

import httpx

from ..models import SearchCandidate

logger = logging.getLogger("news_radar.search.github")

GITHUB_API = "https://api.github.com/search/repositories"


async def search_github(
    term: str,
    max_results: int = 20,
    since_days: int = 90,
    timeout: int = 30,
) -> list[SearchCandidate]:
    """Search GitHub repositories matching term."""
    token = os.environ.get("GITHUB_TOKEN")
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "NewsRadarMVP/0.1",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    
    query = quote_plus(term)
    url = f"{GITHUB_API}?q={query}&sort=updated&order=desc&per_page={max_results}"
    
    logger.info(f"Searching GitHub: '{term}' (max {max_results})")
    
    try:
        async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
        
        data = resp.json()
        items = data.get("items", [])
        candidates = []

        for item in items:
            candidates.append(SearchCandidate(
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
            ))
        
        logger.info(f"GitHub: found {len(candidates)} repos for '{term}'")
        return candidates
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            logger.warning(f"GitHub rate limit hit. Set GITHUB_TOKEN env var.")
        else:
            logger.error(f"GitHub search failed for '{term}': {e}")
        return []
    except Exception as e:
        logger.error(f"GitHub search failed for '{term}': {e}")
        return []
