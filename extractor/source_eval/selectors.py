"""Derive CSS selectors for listing and article pages."""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

logger = logging.getLogger("news_radar.source_eval.selectors")


def derive_listing_selectors(
    html: str,
    base_url: str,
) -> dict[str, str]:
    """Derive CSS selectors for article links on a listing page."""
    soup = BeautifulSoup(html, "lxml")
    base_domain = urlparse(base_url).netloc.replace("www.", "")
    
    # Find containers with multiple article-like links
    best_selector = ""
    best_count = 0
    
    # Try common patterns
    candidates = [
        "article a[href]",
        "h2 a[href]", "h3 a[href]",
        ".post a[href]", ".article a[href]",
        ".entry a[href]", ".story a[href]",
        ".card a[href]", ".item a[href]",
        "a.post-link", "a.article-link",
    ]
    
    for sel in candidates:
        links = soup.select(sel)
        # Filter to same-domain links
        valid = []
        for a in links:
            href = a.get("href", "")
            full = urljoin(base_url, href)
            domain = urlparse(full).netloc.replace("www.", "")
            if base_domain in domain:
                valid.append(full)
        
        if len(valid) > best_count:
            best_count = len(valid)
            best_selector = sel
    
    result = {}
    if best_selector and best_count >= 3:
        result["article_link_css"] = best_selector
    
    return result


def derive_article_selectors(html: str) -> dict[str, str]:
    """Derive CSS selectors for article content."""
    soup = BeautifulSoup(html, "lxml")
    selectors = {}
    
    # Title
    h1 = soup.find("h1")
    if h1:
        selectors["title_css"] = "h1"
    
    # Date
    time_el = soup.find("time", datetime=True)
    if time_el:
        selectors["date_css"] = "time[datetime]"
    
    # Content
    article = soup.find("article")
    if article:
        selectors["content_css"] = "article"
    else:
        main = soup.find("main")
        if main:
            selectors["content_css"] = "main"
    
    # Canonical
    canonical = soup.find("link", rel="canonical")
    if canonical:
        selectors["canonical_css"] = "link[rel='canonical']"
    
    # JSON-LD
    jsonld = soup.find("script", type="application/ld+json")
    if jsonld:
        selectors["jsonld_detected"] = "true"
    
    return selectors
