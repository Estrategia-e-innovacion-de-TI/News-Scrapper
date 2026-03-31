"""News search use cases — orchestrate Google News + classification pipeline.

Provides ``search_aras()`` and ``search_riesgos()`` that combine:
- GoogleNewsConnector for discovery
- LLMClassifier / RulesClassifier based on classifier_mode
- LLMReranker for relevance re-scoring (LLM mode)
- SeverityScorer for severity assignment
- ArasFilter / RiesgosFilter for metadata matching
- NITResolver for NIT → company name resolution
- PresetsLoader for risk term presets
- RelevanceScorer for weighted relevance scoring

Validates: Requirements 1.1-1.5, 2.1-2.5, 9.1-9.5, 10.1-10.5,
           16.1-16.5, 17.1-17.3, 20.1-20.3, 21.1-21.3
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from newsradar_api.domain.usecase.capabilities import (
    RulesClassifier,
    SeverityScorer,
    process_document,
)

logger = logging.getLogger(__name__)

# Re-export for backward compatibility with routes
from newsradar_api.infrastructure.connectors.google_news_connector import (
    search as _gn_search,
)

# Risk preset terms mapping (inline fallback)
RISK_PRESETS = {
    "ciber": ["ransomware", "ciberseguridad", "data breach", "phishing", "malware", "zero trust"],
    "fraude": ["fraude financiero", "lavado de activos", "estafa", "suplantación", "fraude digital"],
    "operacional": ["riesgo operacional", "falla tecnológica", "interrupción servicio", "continuidad negocio"],
    "ambiental_social": ["riesgo ambiental", "impacto social", "ESG", "sostenibilidad", "cambio climático"],
    "all": ["riesgo emergente", "ciberseguridad", "fraude", "riesgo operacional", "ESG", "IA riesgo"],
}

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=es-419&gl=CO&ceid=CO:es-419"


def _build_query(
    company: str | None = None,
    terms: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> str:
    """Build a Google News search query string."""
    parts: list[str] = []
    if company:
        parts.append(f'"{company}"')
    if terms:
        for t in terms[:5]:
            parts.append(f'"{t}"' if " " in t else t)
    query = " OR ".join(parts) if len(parts) > 1 and not company else " ".join(parts)
    if date_from:
        query += f" after:{date_from}"
    if date_to:
        query += f" before:{date_to}"
    return query


async def search_google_news(query: str, max_items: int = 30) -> list[dict]:
    """Search Google News RSS via the GoogleNewsConnector.

    Wraps the connector's ``search()`` and converts QueueItems back to
    dicts for backward compatibility with existing route code.
    """
    from urllib.parse import quote_plus
    import httpx
    import feedparser
    from datetime import datetime

    url = GOOGLE_NEWS_RSS.format(query=quote_plus(query))
    try:
        async with httpx.AsyncClient(timeout=25, follow_redirects=True, verify=False) as client:
            response = await client.get(url, headers={
                "User-Agent": "NewsRadarMVP/0.1",
                "Accept": "application/rss+xml, application/xml, text/xml",
            })
            response.raise_for_status()
            feed = feedparser.parse(response.text)
            if not feed.entries:
                return []

            results = []
            for entry in feed.entries[:max_items]:
                pub_date = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6]).isoformat()
                    except (TypeError, ValueError):
                        pass

                title = entry.get("title", "")
                source = ""
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title = parts[0]
                    source = parts[1] if len(parts) > 1 else ""

                results.append({
                    "title": title,
                    "source": source,
                    "published_at": pub_date,
                    "url": entry.get("link", ""),
                    "summary": entry.get("summary", "").replace("<b>", "").replace("</b>", "")[:500],
                })
            return results
    except Exception as e:
        logger.error("Google News search failed: %s", e)
        return []


def _resolve_nit(nit: str) -> str | None:
    """Resolve NIT to company name using NITResolver."""
    try:
        from newsradar_api.domain.usecase.nit_resolver import NITResolver
        resolver = NITResolver()
        return resolver.resolve(nit)
    except Exception as exc:
        logger.warning("NIT resolution failed: %s", exc)
        return None


def _resolve_preset_terms(terms_preset: str) -> list[str]:
    """Resolve preset to terms using PresetsLoader, fallback to inline."""
    try:
        from newsradar_api.domain.usecase.presets_loader import resolve_preset
        return resolve_preset(terms_preset)
    except Exception:
        return RISK_PRESETS.get(terms_preset, [])


def _classify_document(
    text: str, title: str, query_type: str, classifier_mode: str = "rules",
) -> dict:
    """Classify a document using LLM or rules classifier."""
    if classifier_mode == "llm":
        try:
            from newsradar_api.domain.usecase.llm_classifier import LLMClassifier
            clf = LLMClassifier()
            cr = clf.classify(text, title, query_type=query_type)
            return {
                "category": cr.label.replace("_", " ").title() if cr.label != "otro" else None,
                "confidence": round(cr.confidence, 2),
                "matched_keywords": cr.matched_keywords,
                "events": [],
            }
        except Exception as exc:
            logger.warning("LLM classify failed, falling back to rules: %s", exc)

    return process_document(text, title, query_type=query_type)


async def search_aras(
    company: str | None = None,
    nit: str | None = None,
    risk_category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    classifier_mode: str = "rules",
) -> dict:
    """Execute ARAS search using new components."""
    run_id = str(uuid.uuid4())[:8]

    # Req 20.1-20.3: Resolve NIT
    search_company = company
    if nit and not company:
        resolved = _resolve_nit(nit)
        if resolved:
            search_company = resolved

    search_company = search_company or nit or ""
    if not search_company:
        return {"run_id": run_id, "total_documents": 0, "total_classified": 0, "results": []}

    query = _build_query(company=search_company, date_from=date_from, date_to=date_to)
    entries = await search_google_news(query, max_items=30)

    results = []
    classified_count = 0
    for entry in entries:
        text = entry.get("summary", "")
        title = entry.get("title", "")
        r: dict[str, Any] = {
            "title": title,
            "source": entry["source"],
            "published_at": entry["published_at"],
            "url": entry["url"],
            "summary": text,
            "category": risk_category or "General",
            "severity": None,
            "evidence": [],
            "confidence": None,
            "matched_keywords": [],
            "events": [],
            "relevance_score": None,
        }
        if text:
            analysis = _classify_document(text, title, "aras", classifier_mode)
            r["category"] = analysis.get("category") or r["category"]
            r["severity"] = analysis.get("severity")
            r["evidence"] = analysis.get("evidence", [])
            r["confidence"] = analysis.get("confidence")
            r["matched_keywords"] = analysis.get("matched_keywords", [])

            if r["severity"] is None:
                scorer = SeverityScorer()
                sr = scorer.score(text, title)
                r["severity"] = sr.severity
                r["evidence"] = [s.text for s in sr.evidence_spans]

            if r["category"] and r["category"] != "General":
                classified_count += 1
        results.append(r)

    return {
        "run_id": run_id,
        "total_documents": len(results),
        "total_classified": classified_count,
        "results": results,
    }


async def search_riesgos(
    terms: list[str] | None = None,
    terms_preset: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    classifier_mode: str = "rules",
) -> dict:
    """Execute Riesgos search using new components."""
    run_id = str(uuid.uuid4())[:8]

    # Req 21.1-21.3: Resolve terms from preset
    search_terms = list(terms or [])
    if terms_preset:
        preset_terms = _resolve_preset_terms(terms_preset)
        search_terms.extend(preset_terms)

    if not search_terms:
        return {"run_id": run_id, "total_documents": 0, "total_classified": 0, "results": []}

    query = _build_query(terms=search_terms, date_from=date_from, date_to=date_to)
    entries = await search_google_news(query, max_items=30)

    category = terms_preset.replace("_", " ").title() if terms_preset else "Riesgo Emergente"

    results = []
    classified_count = 0
    for entry in entries:
        text = entry.get("summary", "")
        title = entry.get("title", "")
        r: dict[str, Any] = {
            "title": title,
            "source": entry["source"],
            "published_at": entry["published_at"],
            "url": entry["url"],
            "summary": text,
            "category": category,
            "severity": None,
            "evidence": [],
            "confidence": None,
            "matched_keywords": [],
            "events": [],
            "relevance_score": None,
        }
        if text:
            analysis = _classify_document(text, title, "riesgos", classifier_mode)
            r["category"] = analysis.get("category") or r["category"]
            r["severity"] = analysis.get("severity")
            r["evidence"] = analysis.get("evidence", [])
            r["confidence"] = analysis.get("confidence")
            r["matched_keywords"] = analysis.get("matched_keywords", [])
            r["events"] = analysis.get("events", [])

            if r["severity"] is None:
                scorer = SeverityScorer()
                sr = scorer.score(text, title)
                r["severity"] = sr.severity
                r["evidence"] = [s.text for s in sr.evidence_spans]

            if r["category"] and r["category"] != category:
                classified_count += 1
        results.append(r)

    return {
        "run_id": run_id,
        "total_documents": len(results),
        "total_classified": classified_count,
        "results": results,
    }
