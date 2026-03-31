"""Metadata extraction from HTML (canonical URL, title, date, author, JSON-LD).

Ported from news_radar_mvp/extractor/extract/metadata.py and adapted to
hexagonal architecture with a class-based interface returning MetadataResult.

Validates: Requirements 4.1-4.5
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from newsradar_api.domain.model.pipeline_models import MetadataResult

logger = logging.getLogger("newsradar.extractors.metadata")


def _parse_date(date_str: str | None) -> str | None:
    """Parse a date string to ISO-8601 format, returning *None* on failure."""
    if not date_str:
        return None
    try:
        dt = date_parser.parse(date_str, fuzzy=True)
        return dt.isoformat()
    except (ValueError, TypeError, OverflowError):
        return None


class MetadataExtractor:
    """Extracts structured metadata from raw HTML.

    Extraction order per field follows the priority defined in Requirements 4.1-4.5:

    * **canonical_url**: ``link[rel=canonical]`` → ``og:url``
    * **title**: ``h1`` → ``og:title`` → ``twitter:title`` → ``<title>`` (strip site suffix)
    * **published_at**: ``article:published_time`` → JSON-LD ``datePublished`` →
      ``<time datetime>`` → meta date/pubdate/publish_date
    * **author**: ``meta[name=author]`` → ``article:author`` → JSON-LD author →
      ``a[rel=author]`` → element with class containing "author"
    * **jsonld**: ``<script type="application/ld+json">`` supporting ``@graph``
      and types Article, NewsArticle, BlogPosting, WebPage
    """

    # JSON-LD types we consider relevant
    _JSONLD_TYPES = {"Article", "NewsArticle", "BlogPosting", "WebPage"}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, html: str) -> MetadataResult:
        """Extract metadata from *html* and return a :class:`MetadataResult`."""
        if not html or not html.strip():
            return MetadataResult()

        soup = BeautifulSoup(html, "lxml")

        return MetadataResult(
            canonical_url=self._extract_canonical(soup),
            title=self._extract_title(soup),
            published_at=self._extract_published_date(soup),
            author=self._extract_author(soup),
            jsonld=self._extract_jsonld(soup),
        )

    # ------------------------------------------------------------------
    # Canonical URL  (Req 4.1)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_canonical(soup: BeautifulSoup) -> str | None:
        # 1. link[rel=canonical]
        link = soup.find("link", rel="canonical")
        if link and link.get("href"):
            return link["href"]

        # 2. og:url
        og_url = soup.find("meta", property="og:url")
        if og_url and og_url.get("content"):
            return og_url["content"]

        return None

    # ------------------------------------------------------------------
    # Title  (Req 4.2)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str | None:
        # 1. h1
        h1 = soup.find("h1")
        if h1:
            text = h1.get_text(strip=True)
            if text and len(text) > 10:
                return text

        # 2. og:title
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"]

        # 3. twitter:title
        tw_title = soup.find("meta", attrs={"name": "twitter:title"})
        if tw_title and tw_title.get("content"):
            return tw_title["content"]

        # 4. <title> tag — strip site-name suffix
        title_tag = soup.find("title")
        if title_tag:
            text = title_tag.get_text(strip=True)
            text = re.sub(r"\s*[|\-–—]\s*[^|\-–—]+$", "", text)
            if text:
                return text

        return None

    # ------------------------------------------------------------------
    # Published date  (Req 4.3)
    # ------------------------------------------------------------------

    def _extract_published_date(self, soup: BeautifulSoup) -> str | None:
        # 1. article:published_time
        meta = soup.find("meta", property="article:published_time")
        if meta and meta.get("content"):
            return _parse_date(meta["content"])

        # 2. datePublished / dateCreated in JSON-LD
        jsonld = self._extract_jsonld(soup)
        if jsonld:
            date = jsonld.get("datePublished") or jsonld.get("dateCreated")
            if date:
                return _parse_date(date)

        # 3. <time datetime="...">
        time_el = soup.find("time", datetime=True)
        if time_el:
            return _parse_date(time_el["datetime"])

        # 3b. <time> with text content
        time_el = soup.find("time")
        if time_el:
            text = time_el.get_text(strip=True)
            if text:
                return _parse_date(text)

        # 4. meta with date-related names
        for name in ("date", "pubdate", "publish_date", "article:published"):
            meta = soup.find("meta", attrs={"name": name})
            if meta and meta.get("content"):
                return _parse_date(meta["content"])

        return None

    # ------------------------------------------------------------------
    # Author  (Req 4.4)
    # ------------------------------------------------------------------

    def _extract_author(self, soup: BeautifulSoup) -> str | None:
        # 1. meta[name=author]
        meta = soup.find("meta", attrs={"name": "author"})
        if meta and meta.get("content"):
            return meta["content"]

        # 2. article:author
        meta = soup.find("meta", property="article:author")
        if meta and meta.get("content"):
            return meta["content"]

        # 3. JSON-LD author
        jsonld = self._extract_jsonld(soup)
        if jsonld:
            author = jsonld.get("author")
            if isinstance(author, dict):
                return author.get("name")
            if isinstance(author, list) and author:
                first = author[0]
                return first.get("name") if isinstance(first, dict) else str(first)
            if isinstance(author, str):
                return author

        # 4. a[rel=author]
        author_link = soup.find("a", rel="author")
        if author_link:
            return author_link.get_text(strip=True)

        # 5. Element with class containing "author"
        author_el = soup.find(class_=re.compile(r"author", re.I))
        if author_el:
            text = author_el.get_text(strip=True)
            text = re.sub(r"^(by|por|author:?)\s*", "", text, flags=re.I)
            if text and len(text) < 100:
                return text

        return None

    # ------------------------------------------------------------------
    # JSON-LD  (Req 4.5)
    # ------------------------------------------------------------------

    def _extract_jsonld(self, soup: BeautifulSoup) -> dict[str, Any] | None:
        """Extract JSON-LD structured data supporting @graph and article types."""
        scripts = soup.find_all("script", type="application/ld+json")

        for script in scripts:
            try:
                data = json.loads(script.string or "")

                # Handle @graph array
                if isinstance(data, dict) and "@graph" in data:
                    for item in data["@graph"]:
                        if isinstance(item, dict) and item.get("@type") in self._JSONLD_TYPES:
                            return item

                # Direct article object
                if isinstance(data, dict) and data.get("@type") in self._JSONLD_TYPES:
                    return data

                # List of items
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") in self._JSONLD_TYPES:
                            return item

            except (json.JSONDecodeError, TypeError):
                continue

        return None
