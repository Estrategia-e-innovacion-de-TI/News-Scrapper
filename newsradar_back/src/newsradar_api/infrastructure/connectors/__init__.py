"""Infrastructure connectors — catalog, RSS, scrape, Google News.

Connector modules are imported lazily to avoid hard failures when
optional third-party dependencies (feedparser, bs4, googlenewsdecoder)
are not yet installed.  The catalog loader is always available.
"""

from .catalog_loader import (
    CATALOG_DEFAULTS,
    filter_sources,
    load_catalog,
    load_sources,
    merge_defaults,
    parse_source,
)

__all__ = [
    # Catalog
    "CATALOG_DEFAULTS",
    "filter_sources",
    "load_catalog",
    "load_sources",
    "merge_defaults",
    "parse_source",
    # Connector modules (import directly when needed):
    #   from newsradar_api.infrastructure.connectors import rss_connector
    #   from newsradar_api.infrastructure.connectors import scrape_connector
    #   from newsradar_api.infrastructure.connectors import google_news_connector
    "rss_connector",
    "scrape_connector",
    "google_news_connector",
]
