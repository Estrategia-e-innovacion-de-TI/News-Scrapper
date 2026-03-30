"""ArXiv search provider via RSS/Atom API."""
from __future__ import annotations

import logging
from urllib.parse import quote_plus

import feedparser
import httpx

from ..models import SearchCandidate

logger = logging.getLogger("news_radar.search.arxiv")

ARXIV_API = "http://export.arxiv.org/api/query"


async def search_arxiv(
    term: str,
    max_results: int = 20,
    since_days: int = 30,
    timeout: int = 30,
) -> list[SearchCandidate]:
    """Search ArXiv for papers matching term."""
    query = quote_plus(term)
    url = f"{ARXIV_API}?search_query=all:{query}&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    
    logger.info(f"Searching ArXiv: '{term}' (max {max_results})")
    
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, verify=False) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        
        feed = feedparser.parse(resp.text)
        candidates = []
        
        for entry in feed.entries:
            title = entry.get("title", "").replace("\n", " ").strip()
            summary = entry.get("summary", "").replace("\n", " ").strip()
            link = entry.get("link", "")
            published = entry.get("published", "")
            authors = ", ".join(a.get("name", "") for a in entry.get("authors", []))
            
            candidates.append(SearchCandidate(
                mode="papers",
                term=term,
                title=title,
                url=link,
                snippet=summary[:500],
                published_at=published,
                source_provider="arxiv",
                extra={"authors": authors},
            ))
        
        logger.info(f"ArXiv: found {len(candidates)} papers for '{term}'")
        return candidates
        
    except Exception as e:
        logger.error(f"ArXiv search failed for '{term}': {e}")
        return []
