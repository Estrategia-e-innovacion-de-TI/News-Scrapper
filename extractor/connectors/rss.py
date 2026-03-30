"""RSS feed connector."""
from __future__ import annotations

import logging
from datetime import datetime

import feedparser
import httpx

from ..state import FetchMethod, QueueItem, SourceConfig
from ..utils import is_within_days, parse_date, rate_limiter

logger = logging.getLogger("news_radar.rss")


async def fetch_feed(url: str, timeout: int = 25) -> feedparser.FeedParserDict | None:
    """Fetch and parse RSS/Atom feed."""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, verify=False) as client:
            response = await client.get(url, headers={
                "User-Agent": "NewsRadarMVP/0.1 (+contact: security-research@yourorg.com)",
                "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
            })
            response.raise_for_status()
            
            feed = feedparser.parse(response.text)
            
            if feed.bozo and not feed.entries:
                logger.warning(f"Feed parse error for {url}: {feed.bozo_exception}")
                return None
            
            return feed
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching feed {url}: {e.response.status_code}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Request error fetching feed {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching feed {url}: {e}")
        return None


def parse_entry_date(entry: dict) -> str | None:
    """Extract and parse date from feed entry."""
    # Try various date fields
    date_fields = ["published", "updated", "created", "pubDate"]
    
    for field in date_fields:
        if field in entry:
            parsed = parse_date(entry[field])
            if parsed:
                return parsed
    
    # Try parsed versions
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            dt = datetime(*entry.published_parsed[:6])
            return dt.isoformat()
        except (TypeError, ValueError):
            pass
    
    return None


async def discover_rss_items(
    source: SourceConfig,
    days: int = 7,
    max_items: int = 20,
) -> list[QueueItem]:
    """Discover items from RSS feeds."""
    items = []
    
    await rate_limiter.wait(source.source_id, source.rate_limit_rps)
    
    for feed_url in source.rss_urls:
        logger.info(f"[{source.source_id}] Fetching RSS: {feed_url}")
        
        feed = await fetch_feed(feed_url, source.timeout_seconds)
        
        if not feed or not feed.entries:
            logger.warning(f"[{source.source_id}] No entries in feed: {feed_url}")
            continue
        
        for entry in feed.entries[:max_items]:
            # Get URL
            url = entry.get("link", "")
            if not url:
                continue
            
            # Get date and filter
            published = parse_entry_date(entry)
            if not is_within_days(published, days):
                continue
            
            # Get title
            title = entry.get("title", "")
            
            item = QueueItem(
                source_id=source.source_id,
                url=url,
                source_url=feed_url,
                fetch_method=FetchMethod.RSS,
                title=title,
                published_at=published,
                requires_playwright=source.requires_playwright,
            )
            items.append(item)
            
            if len(items) >= max_items:
                break
        
        if len(items) >= max_items:
            break
    
    logger.info(f"[{source.source_id}] Discovered {len(items)} RSS items")
    return items
