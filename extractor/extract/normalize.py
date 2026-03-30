"""URL and text normalization utilities."""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def normalize_url(url: str) -> str:
    """Normalize URL for deduplication and comparison."""
    if not url:
        return ""
    
    parsed = urlparse(url)
    
    # Lowercase scheme and host
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    
    # Remove www prefix
    if netloc.startswith("www."):
        netloc = netloc[4:]
    
    # Normalize path
    path = parsed.path
    # Remove trailing slash (except for root)
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    # Collapse multiple slashes
    path = re.sub(r"/+", "/", path)
    
    # Filter query params (remove tracking)
    tracking_params = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "fbclid", "gclid", "ref", "source", "mc_cid", "mc_eid",
    }
    
    if parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=False)
        filtered = {k: v for k, v in params.items() if k.lower() not in tracking_params}
        query = urlencode(filtered, doseq=True) if filtered else ""
    else:
        query = ""
    
    # Rebuild URL without fragment
    return urlunparse((scheme, netloc, path, "", query, ""))


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text."""
    if not text:
        return ""
    
    # Replace various whitespace with single space
    text = re.sub(r"[\t\r\f\v]+", " ", text)
    # Collapse multiple spaces
    text = re.sub(r" +", " ", text)
    # Collapse multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip lines
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    
    return text.strip()


def normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    if not title:
        return ""
    
    # Lowercase
    title = title.lower()
    # Remove punctuation
    title = re.sub(r"[^\w\s]", "", title)
    # Normalize whitespace
    title = re.sub(r"\s+", " ", title)
    
    return title.strip()


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    if not url:
        return ""
    
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    if domain.startswith("www."):
        domain = domain[4:]
    
    return domain
