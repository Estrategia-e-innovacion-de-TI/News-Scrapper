"""Content fetching connectors — RSS, HTTP, Playwright, PDF.

Each connector implements the ContentFetcher protocol for its
specific content type.
"""
from __future__ import annotations

from typing import Any


class RSSConnector:
    """Fetches and parses RSS/Atom feeds.

    Implements: ContentFetcher protocol for RSS sources.
    """

    def fetch(self, url: str, **kwargs: Any) -> str:
        """Fetch and parse an RSS feed.

        TODO: Port implementation from extractor/nodes/
        """
        raise NotImplementedError("TODO: port RSS connector from extractor")


class HTTPConnector:
    """Fetches web pages via HTTP (httpx).

    Implements: ContentFetcher protocol for HTTP sources.
    """

    def fetch(self, url: str, **kwargs: Any) -> str:
        """Fetch a web page via HTTP.

        TODO: Port implementation from extractor/nodes/
        """
        raise NotImplementedError("TODO: port HTTP connector from extractor")


class PlaywrightConnector:
    """Fetches JavaScript-rendered pages via Playwright.

    Implements: ContentFetcher protocol for browser-required sources.
    """

    def fetch(self, url: str, **kwargs: Any) -> str:
        """Fetch a page using Playwright browser.

        TODO: Port implementation from extractor/nodes/
        """
        raise NotImplementedError("TODO: port Playwright connector from extractor")


class PDFConnector:
    """Fetches and extracts text from PDF documents.

    Implements: ContentFetcher protocol for PDF sources.
    """

    def fetch(self, url: str, **kwargs: Any) -> str:
        """Fetch and extract text from a PDF.

        TODO: Port implementation from extractor/nodes/
        """
        raise NotImplementedError("TODO: port PDF connector from extractor")
