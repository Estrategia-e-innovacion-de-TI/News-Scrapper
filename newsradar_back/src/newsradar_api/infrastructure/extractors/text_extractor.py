"""Text extraction from HTML using trafilatura → readability-lxml → BeautifulSoup fallback chain.

Ported from news_radar_mvp/extractor/extract/text.py and adapted to hexagonal architecture.
Validates: Requirements 3.1-3.6
"""
from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

logger = logging.getLogger("newsradar.extractors.text")

# Boilerplate patterns to strip from extracted text
_BOILERPLATE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"Cookie\s*(policy|settings|preferences)",
        r"Accept\s*(all\s*)?cookies",
        r"We\s*use\s*cookies",
        r"Subscribe\s*to\s*(our\s*)?newsletter",
        r"Sign\s*up\s*for\s*(our\s*)?newsletter",
        r"Share\s*(this\s*)?(article|story|post)",
        r"Follow\s*us\s*on",
        r"©\s*\d{4}",
        r"All\s*rights\s*reserved",
        r"Copyright\s*\d{4}",
    )
]

# Tags to remove in the BS4 fallback
_REMOVE_TAGS = ("script", "style", "nav", "footer", "header", "aside", "noscript")

# Regex for identifying main-content containers by class or id
_CONTENT_RE = re.compile(r"(article|content|post|entry|story)", re.IGNORECASE)


class TextExtractor:
    """Extracts main text from HTML using a three-stage fallback chain.

    Chain order:
      1. trafilatura  (favor_precision=True, no comments/tables)
      2. readability-lxml
      3. BeautifulSoup (removes boilerplate tags, finds main container)
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, html: str, min_chars: int = 800) -> tuple[str, str]:
        """Extract main text from *html*.

        Returns ``(cleaned_text, method_used)`` where *method_used* is one of
        ``"trafilatura"``, ``"readability"``, ``"bs4"``, ``"fallback"``, or
        ``"empty"``.
        """
        if not html or not html.strip():
            return "", "empty"

        # 1. trafilatura — best quality
        text_traf = self._extract_trafilatura(html)
        if text_traf and len(text_traf) >= min_chars:
            return self.clean_text(text_traf), "trafilatura"

        # 2. readability-lxml
        text_read = self._extract_readability(html)
        if text_read and len(text_read) >= min_chars:
            return self.clean_text(text_read), "readability"

        # Accept partial results above half-threshold
        if text_traf and len(text_traf) >= min_chars // 2:
            return self.clean_text(text_traf), "trafilatura"
        if text_read and len(text_read) >= min_chars // 2:
            return self.clean_text(text_read), "readability"

        # 3. BeautifulSoup fallback
        text_bs4 = self._extract_bs4(html)
        if text_bs4:
            return self.clean_text(text_bs4), "bs4"

        # Return whatever we got, cleaned
        best = text_traf or text_read or text_bs4 or ""
        return self.clean_text(best), "fallback"

    # ------------------------------------------------------------------
    # Text cleaning
    # ------------------------------------------------------------------

    @staticmethod
    def clean_text(text: str) -> str:
        """Remove boilerplate noise and normalise whitespace."""
        if not text:
            return ""

        # Normalise line endings and whitespace
        text = re.sub(r"\r\n", "\n", text)
        text = re.sub(r"\t", " ", text)
        text = re.sub(r" +", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Strip boilerplate patterns
        for pattern in _BOILERPLATE_PATTERNS:
            text = pattern.sub("", text)

        # Remove any residual HTML tags that slipped through
        text = re.sub(r"<[^>]+>", "", text)

        return text.strip()

    # ------------------------------------------------------------------
    # Private extraction strategies
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_trafilatura(html: str) -> str | None:
        """Strategy 1: trafilatura with precision mode."""
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
        except Exception as exc:  # noqa: BLE001
            logger.debug("Trafilatura extraction failed: %s", exc)
            return None

    @staticmethod
    def _extract_readability(html: str) -> str | None:
        """Strategy 2: readability-lxml."""
        try:
            from readability import Document

            doc = Document(html)
            summary_html = doc.summary()

            soup = BeautifulSoup(summary_html, "lxml")
            text = soup.get_text(separator="\n", strip=True)
            return text if text else None
        except Exception as exc:  # noqa: BLE001
            logger.debug("Readability extraction failed: %s", exc)
            return None

    @staticmethod
    def _extract_bs4(html: str) -> str | None:
        """Strategy 3: BeautifulSoup with tag removal and container search."""
        try:
            soup = BeautifulSoup(html, "lxml")

            # Remove unwanted tags
            for tag in soup.find_all(_REMOVE_TAGS):
                tag.decompose()

            # Find main content container
            main_content = (
                soup.find("article")
                or soup.find("main")
                or soup.find(class_=_CONTENT_RE)
                or soup.find(id=_CONTENT_RE)
                or soup.body
            )

            if not main_content:
                return None

            text = main_content.get_text(separator="\n", strip=True)

            # Collapse excessive whitespace
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = re.sub(r" {2,}", " ", text)

            return text.strip() if text else None
        except Exception as exc:  # noqa: BLE001
            logger.debug("BS4 extraction failed: %s", exc)
            return None
