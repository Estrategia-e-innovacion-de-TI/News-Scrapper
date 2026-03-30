"""Utility functions for rate limiting, retries, logging, and time helpers."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable
from urllib.parse import urlparse, urlunparse, urljoin

from dateutil import parser as date_parser


# Configure logging
def setup_logging(debug: bool = False) -> logging.Logger:
    """Setup logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("news_radar")


logger = logging.getLogger("news_radar")


class RateLimiter:
    """Simple rate limiter per source."""
    
    def __init__(self):
        self._last_request: dict[str, float] = {}
    
    async def wait(self, source_id: str, rps: float = 1.0):
        """Wait if needed to respect rate limit."""
        if rps <= 0:
            return
        
        min_interval = 1.0 / rps
        now = time.monotonic()
        last = self._last_request.get(source_id, 0)
        elapsed = now - last
        
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        
        self._last_request[source_id] = time.monotonic()


rate_limiter = RateLimiter()


async def retry_async(
    func: Callable,
    max_retries: int = 2,
    backoff: float = 1.7,
    exceptions: tuple = (Exception,),
) -> Any:
    """Retry async function with exponential backoff."""
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except exceptions as e:
            last_exception = e
            if attempt < max_retries:
                wait_time = backoff ** attempt
                logger.debug(f"Retry {attempt + 1}/{max_retries} after {wait_time:.1f}s: {e}")
                await asyncio.sleep(wait_time)
    
    raise last_exception


def normalize_url(url: str, base_url: str | None = None) -> str:
    """Normalize URL for deduplication."""
    if not url:
        return ""
    
    # Handle relative URLs
    if base_url and not url.startswith(("http://", "https://")):
        url = urljoin(base_url, url)
    
    parsed = urlparse(url)
    
    # Normalize scheme
    scheme = parsed.scheme.lower() or "https"
    
    # Normalize host
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    
    # Remove trailing slash from path
    path = parsed.path.rstrip("/") or "/"
    
    # Remove common tracking params
    # Keep query for now, but could filter utm_* etc.
    
    return urlunparse((scheme, netloc, path, "", "", ""))


def normalize_text(text: str) -> str:
    """Normalize text for hashing/comparison."""
    if not text:
        return ""
    
    # Lowercase
    text = text.lower()
    
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    
    # Remove punctuation for comparison
    text = re.sub(r"[^\w\s]", "", text)
    
    return text.strip()


def compute_hash(title: str, text: str, max_text_len: int = 2000) -> str:
    """Compute SHA256 hash for deduplication."""
    normalized_title = normalize_text(title)
    normalized_text = normalize_text(text)[:max_text_len]
    
    content = f"{normalized_title}|{normalized_text}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def parse_date(date_str: str | None) -> str | None:
    """Parse date string to ISO8601 format."""
    if not date_str:
        return None
    
    try:
        dt = date_parser.parse(date_str, fuzzy=True)
        return dt.isoformat()
    except (ValueError, TypeError):
        return None


def is_within_days(date_str: str | None, days: int) -> bool:
    """Check if date is within N days from now."""
    if not date_str or days <= 0:
        return True  # No filter if no date or days=0
    
    try:
        dt = date_parser.parse(date_str)
        cutoff = datetime.now(dt.tzinfo) - timedelta(days=days)
        return dt >= cutoff
    except (ValueError, TypeError):
        return True  # Include if can't parse


def truncate_text(text: str, max_len: int = 500) -> str:
    """Truncate text to max length, preserving word boundaries."""
    if len(text) <= max_len:
        return text
    
    truncated = text[:max_len]
    last_space = truncated.rfind(" ")
    
    if last_space > max_len * 0.8:
        truncated = truncated[:last_space]
    
    return truncated.rstrip() + "..."


def detect_language(text: str) -> str:
    """Simple language detection based on common words."""
    if not text:
        return "unknown"
    
    text_lower = text.lower()
    
    # Spanish indicators
    es_words = ["el", "la", "los", "las", "de", "en", "que", "por", "con", "para", "es", "son"]
    es_count = sum(1 for w in es_words if f" {w} " in f" {text_lower} ")
    
    # English indicators
    en_words = ["the", "is", "are", "was", "were", "of", "in", "to", "for", "with", "on", "at"]
    en_count = sum(1 for w in en_words if f" {w} " in f" {text_lower} ")
    
    # Portuguese indicators
    pt_words = ["o", "a", "os", "as", "de", "em", "que", "por", "com", "para", "é", "são"]
    pt_count = sum(1 for w in pt_words if f" {w} " in f" {text_lower} ")
    
    counts = {"es": es_count, "en": en_count, "pt": pt_count}
    max_lang = max(counts, key=counts.get)
    
    if counts[max_lang] >= 3:
        return max_lang
    
    return "unknown"


def is_article_url(url: str, base_url: str = "") -> bool:
    """Heuristic to detect if URL looks like an article."""
    if not url:
        return False
    
    parsed = urlparse(url)
    path = parsed.path.lower()
    
    # Skip common non-article patterns
    skip_patterns = [
        "/tag/", "/tags/", "/category/", "/categories/",
        "/author/", "/authors/", "/page/", "/search",
        "/login", "/register", "/subscribe", "/contact",
        "/about", "/privacy", "/terms", "/rss", "/feed",
        ".xml", ".json", ".pdf", ".jpg", ".png", ".gif",
    ]
    
    if any(p in path for p in skip_patterns):
        return False
    
    # Positive patterns (article-like)
    article_patterns = [
        r"/\d{4}/\d{2}/",  # /2024/03/
        r"/\d{4}-\d{2}-\d{2}",  # /2024-03-09
        r"/news/", r"/noticias/", r"/article/", r"/articulo/",
        r"/post/", r"/blog/", r"/story/", r"/noticia/",
    ]
    
    if any(re.search(p, path) for p in article_patterns):
        return True
    
    # Check for slug-like paths (words separated by hyphens)
    slug_pattern = r"/[\w]+-[\w]+-[\w]+"
    if re.search(slug_pattern, path):
        return True
    
    # If path has reasonable depth, might be article
    segments = [s for s in path.split("/") if s]
    if len(segments) >= 2:
        return True
    
    return False
