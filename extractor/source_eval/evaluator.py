"""Main evaluator logic for profiling new sources."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import httpx
import yaml

from ..extract.text import extract_text
from .discover import check_requires_js, detect_paywall_signals, discover_feeds
from .outputs import save_catalog_patch, save_scorecard
from .selectors import derive_article_selectors, derive_listing_selectors

logger = logging.getLogger("news_radar.source_eval")

KNOWN_PROVIDERS = {
    "github.com": "github",
    "arxiv.org": "arxiv",
    "patents.google.com": "google_patents",
    "huggingface.co": "huggingface",
}


def load_new_sources(path: str | Path) -> list[dict[str, Any]]:
    """Load new sources YAML."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("sources", data) if isinstance(data, dict) else data


async def evaluate_single_news(
    source: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate a single news source."""
    source_id = source.get("source_id", source.get("name", "unknown"))
    url = source.get("url", source.get("base_url", ""))
    
    logger.info(f"[{source_id}] Evaluating news source: {url}")
    
    result = {
        "source_id": source_id,
        "url": url,
        "type": source.get("type", "news"),
        "rss_urls": [],
        "requires_playwright": False,
        "paywall_signals": [],
        "selectors": {},
        "validation": {"sample_urls": [], "ok_count": 0, "failures": []},
        "recommended_type": "scrape",
        "notes": "",
    }

    # 1. Discover feeds
    feeds = await discover_feeds(url)
    result["rss_urls"] = feeds.get("rss_urls", []) + feeds.get("atom_urls", [])
    
    if result["rss_urls"]:
        result["recommended_type"] = "rss"
        result["notes"] = f"RSS detected: {len(result['rss_urls'])} feeds"
        return result
    
    # 2. Check if requires JS
    requires_js = await check_requires_js(url)
    result["requires_playwright"] = requires_js
    
    # 3. Fetch listing page and derive selectors
    try:
        async with httpx.AsyncClient(
            timeout=20, follow_redirects=True, verify=False,
        ) as client:
            resp = await client.get(url, headers={
                "User-Agent": "NewsRadarMVP/0.1 SourceEval",
            })
            
            if resp.status_code == 403:
                result["notes"] = "Blocked (403)"
                result["paywall_signals"].append("403")
                return result
            
            if resp.status_code == 200:
                html = resp.text
                
                # Paywall check
                signals = await detect_paywall_signals(url, html)
                result["paywall_signals"] = signals
                
                # Derive selectors
                listing_sel = derive_listing_selectors(html, url)
                result["selectors"].update(listing_sel)
                
                # Validate with sample articles
                from bs4 import BeautifulSoup
                from urllib.parse import urljoin
                
                soup = BeautifulSoup(html, "lxml")
                sel = listing_sel.get("article_link_css", "a[href]")
                sample_links = []
                for a in soup.select(sel)[:3]:
                    href = a.get("href", "")
                    if href:
                        sample_links.append(urljoin(url, href))
                
                ok_count = 0
                for sample_url in sample_links:
                    result["validation"]["sample_urls"].append(sample_url)
                    try:
                        r = await client.get(sample_url, headers={
                            "User-Agent": "NewsRadarMVP/0.1",
                        })
                        if r.status_code == 200:
                            text, _ = extract_text(r.text, min_chars=200)
                            if text and len(text) >= 200:
                                ok_count += 1
                                art_sel = derive_article_selectors(r.text)
                                result["selectors"].update(art_sel)
                            else:
                                result["validation"]["failures"].append({
                                    "url": sample_url, "reason": "empty",
                                })
                        else:
                            result["validation"]["failures"].append({
                                "url": sample_url, "reason": str(r.status_code),
                            })
                    except Exception as e:
                        result["validation"]["failures"].append({
                            "url": sample_url, "reason": str(e)[:100],
                        })
                    
                    await asyncio.sleep(1)
                
                result["validation"]["ok_count"] = ok_count
    
    except Exception as e:
        result["notes"] = f"Evaluation error: {e}"
    
    return result


async def evaluate_non_news(source: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a non-news source (repo/patent/paper)."""
    source_id = source.get("source_id", source.get("name", "unknown"))
    url = source.get("url", "")
    source_type = source.get("type", "unknown")
    
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.lower()
    
    provider = None
    for known_domain, prov in KNOWN_PROVIDERS.items():
        if known_domain in domain:
            provider = prov
            break
    
    return {
        "source_id": source_id,
        "url": url,
        "type": source_type,
        "provider": provider,
        "recommended_type": source_type if provider else "custom_pending",
        "notes": f"Mapped to provider: {provider}" if provider else "Custom connector needed",
    }


async def evaluate_sources(
    input_path: str | Path,
    out_dir: str | Path,
) -> list[dict[str, Any]]:
    """Evaluate all sources from input file."""
    sources = load_new_sources(input_path)
    out_dir = Path(out_dir)
    
    evaluations = []
    
    for source in sources:
        source_type = source.get("type", "news")
        
        if source_type == "news":
            ev = await evaluate_single_news(source)
        else:
            ev = await evaluate_non_news(source)
        
        evaluations.append(ev)
    
    # Save outputs
    save_catalog_patch(evaluations, out_dir)
    save_scorecard(evaluations, out_dir)
    
    logger.info(f"Evaluated {len(evaluations)} sources -> {out_dir}")
    
    return evaluations
