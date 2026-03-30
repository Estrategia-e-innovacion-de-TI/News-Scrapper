"""EPO Open Patent Services (OPS) search provider.

Searches patents published in the last N days matching search terms.
Retrieves title + abstract for each patent for downstream relevance scoring.

Requires environment variables:
  EPO_CONSUMER_KEY    — from https://developers.epo.org
  EPO_CONSUMER_SECRET — from https://developers.epo.org
"""
from __future__ import annotations

import logging
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any

import httpx

from ..models import SearchCandidate

logger = logging.getLogger("news_radar.search.patents")

_TOKEN_URL = "https://ops.epo.org/3.2/auth/accesstoken"
_SEARCH_URL = "https://ops.epo.org/3.2/rest-services/published-data/search"
_BIBLIO_URL = "https://ops.epo.org/3.2/rest-services/published-data/publication/epodoc"

# EPO OPS namespaces
_NS = {
    "ops": "http://ops.epo.org",
    "exch": "http://www.epo.org/exchange",
}


async def _get_access_token() -> str | None:
    key = os.environ.get("EPO_CONSUMER_KEY", "")
    secret = os.environ.get("EPO_CONSUMER_SECRET", "")
    if not key or not secret:
        logger.warning(
            "EPO_CONSUMER_KEY/SECRET not set — skipping patent search. "
            "Register at https://developers.epo.org"
        )
        return None
    try:
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            resp = await client.post(
                _TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=(key, secret),
            )
            resp.raise_for_status()
            return resp.json()["access_token"]
    except Exception as exc:
        logger.error("EPO token request failed: %s", exc)
        return None


def _parse_search_xml(xml_text: str) -> list[dict]:
    """Parse EPO search XML response to extract document references."""
    results = []
    try:
        root = ET.fromstring(xml_text)
        for ref in root.iter("{http://www.epo.org/exchange}publication-reference"):
            doc_id = ref.find("{http://www.epo.org/exchange}document-id")
            if doc_id is None:
                continue
            country_el = doc_id.find("{http://www.epo.org/exchange}country")
            docnum_el = doc_id.find("{http://www.epo.org/exchange}doc-number")
            kind_el = doc_id.find("{http://www.epo.org/exchange}kind")
            country = country_el.text if country_el is not None else ""
            doc_number = docnum_el.text if docnum_el is not None else ""
            kind = kind_el.text if kind_el is not None else ""
            if doc_number:
                results.append({
                    "country": country,
                    "doc_number": doc_number,
                    "kind": kind,
                    "epodoc": f"{country}.{doc_number}.{kind}".strip("."),
                })
    except ET.ParseError as exc:
        logger.error("XML parse error: %s", exc)
    return results


def _parse_biblio_xml(xml_text: str) -> dict[str, dict]:
    """Parse EPO biblio XML to extract titles and abstracts."""
    patents: dict[str, dict] = {}
    try:
        root = ET.fromstring(xml_text)
        for doc in root.iter("{http://www.epo.org/exchange}exchange-document"):
            country = doc.get("country", "")
            doc_number = doc.get("doc-number", "")
            kind = doc.get("kind", "")
            date_pub = doc.get("date-publ", "")
            key = f"{country}{doc_number}{kind}"

            # Title (prefer English)
            title = ""
            for t in doc.iter("{http://www.epo.org/exchange}invention-title"):
                lang = t.get("lang", "")
                text = t.text or ""
                if lang == "en" or not title:
                    title = text.strip()

            # Abstract (prefer English)
            abstract = ""
            for ab in doc.iter("{http://www.epo.org/exchange}abstract"):
                lang = ab.get("lang", "")
                parts = []
                for p in ab.iter("{http://www.epo.org/exchange}p"):
                    if p.text:
                        parts.append(p.text.strip())
                text = " ".join(parts)
                if lang == "en" or not abstract:
                    abstract = text

            # Applicants
            applicants = []
            for app in doc.iter("{http://www.epo.org/exchange}applicant"):
                name_el = app.find("{http://www.epo.org/exchange}name")
                if name_el is not None and name_el.text:
                    applicants.append(name_el.text.strip())

            patents[key] = {
                "title": title,
                "abstract": abstract[:500],
                "applicants": applicants[:3],
                "date_published": date_pub,
                "country": country,
                "doc_number": doc_number,
                "kind": kind,
            }
    except ET.ParseError as exc:
        logger.error("Biblio XML parse error: %s", exc)
    return patents


async def search_epo_patents(
    term: str,
    max_results: int = 25,
    since_days: int = 30,
    timeout: int = 30,
) -> list[SearchCandidate]:
    """Search patents via EPO OPS: term + date range, then fetch biblio."""
    token = await _get_access_token()
    if not token:
        return []

    date_from = (datetime.utcnow() - timedelta(days=since_days)).strftime("%Y%m%d")
    date_to = datetime.utcnow().strftime("%Y%m%d")

    # CQL: keyword in title + publication date range
    # Use weekly chunks to avoid EPO 413 "Request Entity Too Large"
    all_doc_refs: list[dict] = []
    chunk_days = 7
    start = datetime.utcnow() - timedelta(days=since_days)
    end = datetime.utcnow()

    while start < end and len(all_doc_refs) < max_results:
        chunk_end = min(start + timedelta(days=chunk_days), end)
        d_from = start.strftime("%Y%m%d")
        d_to = chunk_end.strftime("%Y%m%d")
        cql = f'ti="{term}" AND pd>={d_from} AND pd<={d_to}'
        logger.info("EPO search: '%s' (pd=%s..%s)", term, d_from, d_to)

        try:
            remaining = max_results - len(all_doc_refs)
            async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
                resp = await client.get(
                    _SEARCH_URL,
                    params={"q": cql, "Range": f"1-{min(remaining, 25)}"},
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/xml",
                    },
                )
                if resp.status_code == 404:
                    pass  # no results for this chunk
                elif resp.status_code == 413:
                    logger.warning("EPO 413 for '%s' chunk %s-%s, narrowing", term, d_from, d_to)
                else:
                    resp.raise_for_status()
                    refs = _parse_search_xml(resp.text)
                    all_doc_refs.extend(refs)
        except Exception as exc:
            logger.warning("EPO chunk search failed: %s", exc)

        start = chunk_end + timedelta(days=1)

    doc_refs = all_doc_refs[:max_results]
    if not doc_refs:
        logger.info("EPO: 0 parsed results for '%s'", term)
        return []

    logger.info("EPO: %d document refs for '%s', fetching biblio...", len(doc_refs), term)

    # Step 2: Fetch bibliographic data (title + abstract) in batches
    all_patents: dict[str, dict] = {}
    batch_size = 20
    for i in range(0, len(doc_refs), batch_size):
        batch = doc_refs[i:i + batch_size]
        epodocs = ",".join(d["epodoc"] for d in batch)
        try:
            async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
                biblio_resp = await client.get(
                    f"{_BIBLIO_URL}/{epodocs}/biblio",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/xml",
                    },
                )
                if biblio_resp.status_code == 200:
                    patents = _parse_biblio_xml(biblio_resp.text)
                    all_patents.update(patents)
        except Exception as exc:
            logger.warning("EPO biblio fetch failed for batch: %s", exc)

    # Step 3: Build candidates
    candidates: list[SearchCandidate] = []
    for ref in doc_refs:
        key = f"{ref['country']}{ref['doc_number']}{ref['kind']}"
        patent = all_patents.get(key, {})
        title = patent.get("title", "")
        abstract = patent.get("abstract", "")
        applicants = patent.get("applicants", [])
        date_pub = patent.get("date_published", "")

        display_title = f"[{ref['country']} {ref['doc_number']}] {title}" if title else f"[{key}] Patent"
        snippet = abstract
        if applicants:
            snippet = f"[{', '.join(applicants)}] {abstract}"

        # Format date
        pub_at = None
        if date_pub and len(date_pub) == 8:
            pub_at = f"{date_pub[:4]}-{date_pub[4:6]}-{date_pub[6:8]}"

        candidates.append(SearchCandidate(
            mode="patents",
            term=term,
            title=display_title,
            url=f"https://worldwide.espacenet.com/patent/search?q={key}",
            snippet=snippet[:500],
            source_provider="epo_ops",
            published_at=pub_at,
        ))

    logger.info("EPO: %d patents with biblio for '%s'", len(candidates), term)
    return candidates
