"""Metadata extraction from HTML (canonical, title, date, author, JSON-LD)."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from bs4 import BeautifulSoup

from ..utils import parse_date

logger = logging.getLogger("news_radar.extract.metadata")


def extract_canonical(soup: BeautifulSoup) -> str | None:
    """Extract canonical URL."""
    # link rel=canonical
    link = soup.find("link", rel="canonical")
    if link and link.get("href"):
        return link["href"]
    
    # og:url
    og_url = soup.find("meta", property="og:url")
    if og_url and og_url.get("content"):
        return og_url["content"]
    
    return None


def extract_title(soup: BeautifulSoup) -> str | None:
    """Extract article title."""
    # Try h1 first
    h1 = soup.find("h1")
    if h1:
        text = h1.get_text(strip=True)
        if text and len(text) > 10:
            return text
    
    # og:title
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return og_title["content"]
    
    # twitter:title
    tw_title = soup.find("meta", attrs={"name": "twitter:title"})
    if tw_title and tw_title.get("content"):
        return tw_title["content"]
    
    # title tag
    title_tag = soup.find("title")
    if title_tag:
        text = title_tag.get_text(strip=True)
        # Remove site name suffix
        text = re.sub(r"\s*[|\-–—]\s*[^|\-–—]+$", "", text)
        if text:
            return text
    
    return None


def extract_published_date(soup: BeautifulSoup) -> str | None:
    """Extract publication date."""
    # article:published_time
    meta = soup.find("meta", property="article:published_time")
    if meta and meta.get("content"):
        return parse_date(meta["content"])
    
    # datePublished in JSON-LD
    jsonld = extract_jsonld(soup)
    if jsonld:
        date = jsonld.get("datePublished") or jsonld.get("dateCreated")
        if date:
            return parse_date(date)
    
    # time element with datetime
    time_el = soup.find("time", datetime=True)
    if time_el:
        return parse_date(time_el["datetime"])
    
    # time element with content
    time_el = soup.find("time")
    if time_el:
        text = time_el.get_text(strip=True)
        if text:
            return parse_date(text)
    
    # meta date
    for name in ["date", "pubdate", "publish_date", "article:published"]:
        meta = soup.find("meta", attrs={"name": name})
        if meta and meta.get("content"):
            return parse_date(meta["content"])
    
    return None


def extract_author(soup: BeautifulSoup) -> str | None:
    """Extract author name."""
    # meta author
    meta = soup.find("meta", attrs={"name": "author"})
    if meta and meta.get("content"):
        return meta["content"]
    
    # article:author
    meta = soup.find("meta", property="article:author")
    if meta and meta.get("content"):
        return meta["content"]
    
    # JSON-LD author
    jsonld = extract_jsonld(soup)
    if jsonld:
        author = jsonld.get("author")
        if isinstance(author, dict):
            return author.get("name")
        elif isinstance(author, list) and author:
            first = author[0]
            if isinstance(first, dict):
                return first.get("name")
            return str(first)
        elif isinstance(author, str):
            return author
    
    # rel=author link
    author_link = soup.find("a", rel="author")
    if author_link:
        return author_link.get_text(strip=True)
    
    # class containing author
    author_el = soup.find(class_=re.compile(r"author", re.I))
    if author_el:
        text = author_el.get_text(strip=True)
        # Clean up common prefixes
        text = re.sub(r"^(by|por|author:?)\s*", "", text, flags=re.I)
        if text and len(text) < 100:
            return text
    
    return None


def extract_jsonld(soup: BeautifulSoup) -> dict[str, Any] | None:
    """Extract JSON-LD structured data."""
    scripts = soup.find_all("script", type="application/ld+json")
    
    for script in scripts:
        try:
            data = json.loads(script.string or "")
            
            # Handle @graph
            if isinstance(data, dict) and "@graph" in data:
                for item in data["@graph"]:
                    if item.get("@type") in ["Article", "NewsArticle", "BlogPosting", "WebPage"]:
                        return item
            
            # Direct article
            if isinstance(data, dict):
                if data.get("@type") in ["Article", "NewsArticle", "BlogPosting", "WebPage"]:
                    return data
            
            # List of items
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("@type") in ["Article", "NewsArticle", "BlogPosting"]:
                        return item
                        
        except (json.JSONDecodeError, TypeError):
            continue
    
    return None


def extract_metadata(html: str) -> dict[str, Any]:
    """Extract all metadata from HTML."""
    soup = BeautifulSoup(html, "lxml")
    
    return {
        "canonical_url": extract_canonical(soup),
        "title": extract_title(soup),
        "published_at": extract_published_date(soup),
        "author": extract_author(soup),
        "jsonld": extract_jsonld(soup),
    }
