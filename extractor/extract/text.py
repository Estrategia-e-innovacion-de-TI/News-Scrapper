"""Text extraction from HTML using trafilatura, readability, and bs4."""
from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

logger = logging.getLogger("news_radar.extract.text")


def extract_with_trafilatura(html: str) -> str | None:
    """Extract main text using trafilatura."""
    try:
        import trafilatura
        
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
            favor_precision=True,
        )
        
        return text if text else None
        
    except Exception as e:
        logger.debug(f"Trafilatura extraction failed: {e}")
        return None


def extract_with_readability(html: str) -> str | None:
    """Extract main text using readability-lxml."""
    try:
        from readability import Document
        
        doc = Document(html)
        summary_html = doc.summary()
        
        # Convert to plain text
        soup = BeautifulSoup(summary_html, "lxml")
        text = soup.get_text(separator="\n", strip=True)
        
        return text if text else None
        
    except Exception as e:
        logger.debug(f"Readability extraction failed: {e}")
        return None


def extract_with_bs4(html: str) -> str | None:
    """Extract visible text using BeautifulSoup as fallback."""
    try:
        soup = BeautifulSoup(html, "lxml")
        
        # Remove script, style, nav, footer, header, aside
        for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()
        
        # Try to find main content area
        main_content = (
            soup.find("article") or
            soup.find("main") or
            soup.find(class_=re.compile(r"(article|content|post|entry|story)", re.I)) or
            soup.find(id=re.compile(r"(article|content|post|entry|story)", re.I)) or
            soup.body
        )
        
        if not main_content:
            return None
        
        # Get text
        text = main_content.get_text(separator="\n", strip=True)
        
        # Clean up excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        
        return text.strip() if text else None
        
    except Exception as e:
        logger.debug(f"BS4 extraction failed: {e}")
        return None


def extract_text(html: str, min_chars: int = 800) -> tuple[str | None, str]:
    """
    Extract main text from HTML using multiple strategies.
    Returns (text, method_used).
    """
    if not html:
        return None, "empty"
    
    # Try trafilatura first (best quality)
    text = extract_with_trafilatura(html)
    if text and len(text) >= min_chars:
        return text, "trafilatura"
    
    # Try readability as fallback
    text_readability = extract_with_readability(html)
    if text_readability and len(text_readability) >= min_chars:
        return text_readability, "readability"
    
    # Use best result so far if above threshold
    if text and len(text) >= min_chars // 2:
        return text, "trafilatura"
    if text_readability and len(text_readability) >= min_chars // 2:
        return text_readability, "readability"
    
    # Final fallback: bs4
    text_bs4 = extract_with_bs4(html)
    if text_bs4:
        return text_bs4, "bs4"
    
    # Return whatever we got
    return text or text_readability or text_bs4, "fallback"


def clean_text(text: str) -> str:
    """Clean extracted text."""
    if not text:
        return ""
    
    # Normalize whitespace
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\t", " ", text)
    text = re.sub(r" +", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    # Remove common boilerplate patterns
    boilerplate = [
        r"Cookie\s*(policy|settings|preferences)",
        r"Accept\s*(all\s*)?cookies",
        r"Subscribe\s*to\s*(our\s*)?newsletter",
        r"Sign\s*up\s*for\s*(our\s*)?newsletter",
        r"Share\s*(this\s*)?(article|story|post)",
        r"Follow\s*us\s*on",
        r"©\s*\d{4}",
        r"All\s*rights\s*reserved",
    ]
    
    for pattern in boilerplate:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    
    return text.strip()
