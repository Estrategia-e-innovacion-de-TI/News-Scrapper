"""Playwright browser connector for JS-heavy sites."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Browser, Page

logger = logging.getLogger("news_radar.browser")

# Global browser instance
_browser: "Browser | None" = None
_browser_lock = asyncio.Lock()


async def get_browser() -> "Browser":
    """Get or create browser instance."""
    global _browser
    
    async with _browser_lock:
        if _browser is None:
            try:
                from playwright.async_api import async_playwright
                
                pw = await async_playwright().start()
                _browser = await pw.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                logger.info("Playwright browser started")
            except ImportError:
                raise ImportError(
                    "Playwright not installed. Run: pip install playwright && playwright install chromium"
                )
        
        return _browser


async def close_browser():
    """Close browser instance."""
    global _browser
    
    async with _browser_lock:
        if _browser:
            await _browser.close()
            _browser = None
            logger.info("Playwright browser closed")


async def fetch_with_browser(
    url: str,
    timeout: int = 30,
    wait_for: str | None = None,
) -> tuple[str | None, int, str | None]:
    """
    Fetch page using Playwright browser.
    Returns (html, status_code, error_type).
    """
    try:
        browser = await get_browser()
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        
        page = await context.new_page()
        
        try:
            response = await page.goto(
                url,
                timeout=timeout * 1000,
                wait_until="domcontentloaded",
            )
            
            status = response.status if response else 0
            
            # Wait for content if specified
            if wait_for:
                try:
                    await page.wait_for_selector(wait_for, timeout=5000)
                except Exception:
                    pass  # Continue even if selector not found
            
            # Small delay for JS rendering
            await asyncio.sleep(1)
            
            html = await page.content()
            
            error_type = None
            if status == 403:
                error_type = "403"
            elif status == 402:
                error_type = "paywall"
            elif status >= 400:
                error_type = "unknown"
            
            return html, status, error_type
            
        finally:
            await page.close()
            await context.close()
            
    except asyncio.TimeoutError:
        logger.error(f"Timeout fetching {url} with browser")
        return None, 0, "timeout"
    except Exception as e:
        logger.error(f"Browser error fetching {url}: {e}")
        return None, 0, "unknown"


async def fetch_listing_with_browser(
    url: str,
    selector: str | None = None,
    timeout: int = 30,
) -> tuple[str | None, list[str]]:
    """
    Fetch listing page and extract links using browser.
    Returns (html, links).
    """
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    
    html, status, error = await fetch_with_browser(url, timeout)
    
    if not html or error:
        return None, []
    
    links = []
    soup = BeautifulSoup(html, "lxml")
    
    if selector:
        for element in soup.select(selector):
            href = element.get("href")
            if href:
                links.append(urljoin(url, href))
    else:
        for a in soup.find_all("a", href=True):
            href = a.get("href")
            if href:
                links.append(urljoin(url, href))
    
    return html, links
