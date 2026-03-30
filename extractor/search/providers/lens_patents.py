"""LENS.org patent search provider.

Uses the LENS.org Patent Search API (https://docs.api.lens.org/)
to find patents by keyword in title/abstract/claims.

Requires a LENS_API_TOKEN environment variable (free at https://www.lens.org).
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta

import httpx

from ..models import SearchCandidate

logger = logging.getLogger("news_radar.search.patents")

LENS_API_URL = "https://api.lens.org/patent/search"


async def search_lens_patents(
    term: str,
    max_results: int = 20,
    since_days: int = 180,
    timeout: int = 30,
) -> list[SearchCandidate]:
    """Search patents via LENS.org API.

    Parameters
    ----------
    term : str
        Search query (matched against title, abstract, claims).
    max_results : int
        Maximum patents to return.
    since_days : int
        Only return patents published in the last N days.
    timeout : int
        HTTP request timeout.

    Returns
    -------
    list[SearchCandidate]
        Patent candidates found.
    """
    token = os.environ.get("LENS_API_TOKEN", "")
    if not token:
        logger.warning(
            "LENS_API_TOKEN not set — skipping patent search. "
            "Get a free token at https://www.lens.org"
        )
        return []

    date_from = (datetime.utcnow() - timedelta(days=since_days)).strftime("%Y-%m-%d")

    query_body = {
        "query": {
            "bool": {
                "must": [
                    {
                        "bool": {
                            "should": [
                                {"match": {"title": term}},
                                {"match": {"abstract": term}},
                                {"match": {"claim": term}},
                            ]
                        }
                    },
                    {
                        "range": {
                            "date_published": {"gte": date_from}
                        }
                    },
                ]
            }
        },
        "size": min(max_results, 50),
        "sort": [{"date_published": "desc"}],
        "include": [
            "lens_id",
            "biblio.publication_reference",
            "biblio.invention_title",
            "abstract",
            "biblio.parties.applicants",
            "date_published",
            "jurisdiction",
        ],
    }

    logger.info("LENS patent search: '%s' (since %s, max %d)", term, date_from, max_results)

    try:
        async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
            resp = await client.post(
                LENS_API_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                content=json.dumps(query_body),
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "LENS API error for '%s': HTTP %d — %s",
            term, exc.response.status_code, exc.response.text[:200],
        )
        return []
    except Exception as exc:
        logger.error("LENS patent search failed for '%s': %s", term, exc)
        return []

    results = data.get("data", [])
    total = data.get("total", 0)
    logger.info("LENS patents: %d results (total=%d) for '%s'", len(results), total, term)

    candidates: list[SearchCandidate] = []
    for patent in results:
        # Extract title
        titles = patent.get("biblio", {}).get("invention_title", [])
        title = ""
        for t in titles:
            if isinstance(t, dict):
                title = t.get("text", "")
                if t.get("lang") == "en":
                    break  # prefer English title
            elif isinstance(t, str):
                title = t
                break

        # Extract abstract
        abstracts = patent.get("abstract", [])
        abstract_text = ""
        for a in abstracts:
            if isinstance(a, dict):
                abstract_text = a.get("text", "")
                if a.get("lang") == "en":
                    break
            elif isinstance(a, str):
                abstract_text = a
                break

        # Extract publication reference
        pub_ref = patent.get("biblio", {}).get("publication_reference", {})
        jurisdiction = pub_ref.get("jurisdiction", patent.get("jurisdiction", ""))
        doc_number = pub_ref.get("doc_number", "")
        lens_id = patent.get("lens_id", "")

        # Build URL
        url = f"https://www.lens.org/lens/patent/{lens_id}" if lens_id else ""

        # Extract date
        pub_date = patent.get("date_published", "")

        # Extract applicants
        applicants = patent.get("biblio", {}).get("parties", {}).get("applicants", [])
        applicant_names = []
        for app in applicants[:3]:
            name = app.get("extracted_name", {}).get("value", "")
            if name:
                applicant_names.append(name)

        snippet = abstract_text[:500]
        if applicant_names:
            snippet = f"[{', '.join(applicant_names)}] {snippet}"

        if title:
            candidates.append(
                SearchCandidate(
                    mode="patents",
                    term=term,
                    title=f"[{jurisdiction}{doc_number}] {title}",
                    url=url,
                    snippet=snippet,
                    source_provider="lens_patents",
                    published_at=pub_date,
                )
            )

    return candidates
