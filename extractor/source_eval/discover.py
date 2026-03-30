"""Discover RSS feeds and page structure for new sources."""
from __future__ import annotations

import logging
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("news_radar.source_eval.discover")

COMMON_FEED_PATHS = [
    "/feed", "/rss", "/rss.xml", "/atom.xml", "/feed.xml",
    "/feeds/news/", "/index.xml", "/feed/rss",
]


async def discover_feeds(
    base_url: str,
    timeout: int = 20,
) -> dict[str, list[str]]:
    """Discover RSS/Atom/JSONFeed URLs from a base URL."""
    feeds: dict[str, list[str]] = {
        "rss_urls": [],
        "atom_urls": [],
        "jsonfeed_urls": [],
    }
    
    try:
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=True, verify=False,
        ) as client:
            resp = await client.get(base_url, headers={
                "User-Agent": "NewsRadarMVP/0.1 SourceEval",
            })
            
            if resp.status_code != 200:
                return feeds
            
            soup = BeautifulSoup(resp.text, "lxml")
            
            # Check <link> tags
            for link in soup.find_all("link", rel="alternate"):
                link_type = (link.get("type") or "").lower()
                href = link.get("href", "")
                if not href:
                    continue
                
                full_url = urljoin(base_url, href)

                if "rss" in link_type:
                    feeds["rss_urls"].append(full_url)
                elif "atom" in link_type:
                    feeds["atom_urls"].append(full_url)
                elif "json" in link_type:
                    feeds["jsonfeed_urls"].append(full_url)
            
            # Probe common paths
            for path in COMMON_FEED_PATHS:
                feed_url = urljoin(base_url, path)
                try:
                    r = await client.head(feed_url, follow_redirects=True)
                    ct = (r.headers.get("content-type") or "").lower()
                    if r.status_code == 200 and ("xml" in ct or "rss" in ct or "atom" in ct):
                        if feed_url not in feeds["rss_urls"]:
                            feeds["rss_urls"].append(feed_url)
                except Exception:
                    pass
    
    except Exception as e:
        logger.error(f"Feed discovery failed for {base_url}: {e}")
    
    return feeds


async def detect_paywall_signals(
    url: str,
    html: str,
) -> list[str]:
    """Detect paywall/block signals in HTML."""
    signals = []
    lower = html.lower()
    
    paywall_patterns = [
        "subscribe to read", "suscríbete para leer",
        "paywall", "premium content", "members only",
        "sign in to continue", "create an account",
        "free trial", "unlock this article",
    ]
    
    for pattern in paywall_patterns:
        if pattern in lower:
            signals.append(pattern)
    
    return signals


async def check_requires_js(
    url: str,
    timeout: int = 15,
) -> bool:
    """Check if a page requires JavaScript by comparing content."""
    try:
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=True, verify=False,
        ) as client:
            resp = await client.get(url, headers={
                "User-Agent": "NewsRadarMVP/0.1",
            })
            
            if resp.status_code != 200:
                return True
            
            soup = BeautifulSoup(resp.text, "lxml")
            
            # Remove scripts
            for s in soup.find_all("script"):
                s.decompose()
            
            text = soup.get_text(strip=True)
            
            # If very little text, likely JS-rendered
            if len(text) < 200:
                return True
            
            # Check for common SPA indicators
            body = soup.find("body")
            if body:
                children = list(body.children)
                if len(children) <= 3:
                    divs = body.find_all("div", id=True)
                    if len(divs) <= 2:
                        return True
            
            return False
    except Exception:
        return True
