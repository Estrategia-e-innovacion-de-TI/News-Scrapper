"""Web scraping connector for listing pages and articles."""
from __future__ import annotations

import logging
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from ..state import FetchMethod, QueueItem, SourceConfig
from ..utils import is_article_url, normalize_url, rate_limiter

logger = logging.getLogger("news_radar.scrape")

DEFAULT_HEADERS = {
    "User-Agent": "NewsRadarMVP/0.1 (+contact: security-research@yourorg.com)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es,en;q=0.9",
}


async def fetch_html(
    url: str,
    timeout: int = 25,
    headers: dict | None = None,
) -> tuple[str | None, int]:
    """Fetch HTML content from URL. Returns (html, status_code).
    
    Status code conventions for non-HTTP errors:
      0 = timeout/connection error
      -1 = TLS/SSL error
      -2 = redirect error
    """
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            verify=False,  # Handle SSL issues gracefully
        ) as client:
            response = await client.get(url, headers=headers or DEFAULT_HEADERS)
            return response.text, response.status_code
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching {url}: {e.response.status_code}")
        return None, e.response.status_code
    except httpx.TimeoutException:
        logger.error(f"Timeout fetching {url}")
        return None, 0
    except httpx.ConnectError as e:
        err_str = str(e).lower()
        if "ssl" in err_str or "tls" in err_str or "certificate" in err_str:
            logger.error(f"TLS error fetching {url}: {e}")
            return None, -1
        logger.error(f"Connection error fetching {url}: {e}")
        return None, 0
    except httpx.TooManyRedirects:
        logger.error(f"Too many redirects for {url}")
        return None, -2
    except Exception as e:
        logger.error(f"Unexpected error fetching {url}: {e}")
        return None, 0


def extract_links_by_selector(
    html: str,
    selector: str,
    base_url: str,
) -> list[str]:
    """Extract links using CSS selector."""
    soup = BeautifulSoup(html, "lxml")
    links = []
    
    for element in soup.select(selector):
        href = element.get("href")
        if href:
            full_url = urljoin(base_url, href)
            links.append(full_url)
    
    return links


def extract_links_heuristic(
    html: str,
    base_url: str,
    max_links: int = 50,
) -> list[str]:
    """Extract article links using heuristics."""
    soup = BeautifulSoup(html, "lxml")
    base_domain = urlparse(base_url).netloc.replace("www.", "")
    
    links = []
    seen = set()
    
    # Find all links
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if not href:
            continue
        
        # Build full URL
        full_url = urljoin(base_url, href)
        normalized = normalize_url(full_url)
        
        # Skip if already seen
        if normalized in seen:
            continue
        seen.add(normalized)
        
        # Check if same domain
        link_domain = urlparse(full_url).netloc.replace("www.", "")
        if base_domain not in link_domain:
            continue
        
        # Check if looks like article
        if is_article_url(full_url, base_url):
            links.append(full_url)
            
            if len(links) >= max_links:
                break
    
    return links


async def discover_scrape_items(
    source: SourceConfig,
    max_items: int = 20,
    max_pages: int = 2,
) -> list[QueueItem]:
    """Discover items from listing pages via scraping."""
    items = []
    seen_urls = set()
    
    for listing_url in source.listing_urls[:max_pages]:
        await rate_limiter.wait(source.source_id, source.rate_limit_rps)
        
        logger.info(f"[{source.source_id}] Scraping listing: {listing_url}")
        
        html, status = await fetch_html(listing_url, source.timeout_seconds)
        
        if status == 403:
            logger.warning(f"[{source.source_id}] Blocked (403): {listing_url}")
            continue
        
        if not html:
            logger.warning(f"[{source.source_id}] Failed to fetch: {listing_url}")
            continue
        
        # Extract links
        selector = source.selectors.get("article_link_css")
        
        if selector:
            links = extract_links_by_selector(html, selector, source.base_url or listing_url)
        else:
            links = extract_links_heuristic(html, source.base_url or listing_url)
        
        logger.debug(f"[{source.source_id}] Found {len(links)} links")
        
        for url in links:
            normalized = normalize_url(url)
            if normalized in seen_urls:
                continue
            seen_urls.add(normalized)
            
            item = QueueItem(
                source_id=source.source_id,
                url=url,
                source_url=listing_url,
                fetch_method=FetchMethod.HTTP if not source.requires_playwright else FetchMethod.PLAYWRIGHT,
                requires_playwright=source.requires_playwright,
            )
            items.append(item)
            
            if len(items) >= max_items:
                break
        
        if len(items) >= max_items:
            break
    
    logger.info(f"[{source.source_id}] Discovered {len(items)} scrape items")
    return items


async def fetch_article_html(
    url: str,
    timeout: int = 25,
) -> tuple[str | None, int, str | None]:
    """Fetch article HTML. Returns (html, status_code, error_type)."""
    html, status = await fetch_html(url, timeout)
    
    error_type = None
    if status == 0:
        error_type = "timeout"
    elif status == -1:
        error_type = "tls_error"
    elif status == -2:
        error_type = "redirect_error"
    elif status == 403:
        error_type = "http_403"
    elif status == 402:
        error_type = "paywall"
    elif 400 <= status < 500:
        error_type = "http_4xx"
    elif status >= 500:
        error_type = "http_5xx"
    
    return html, status, error_type
