"""Metadata-only keyword matching for ad-hoc queries.

Matches terms against title/snippet/URL slug WITHOUT fetching full articles.
Ported from news_radar_mvp/extractor/adhoc/match.py
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from urllib.parse import urlparse


@dataclass
class MatchResult:
    """Result of a metadata match."""

    url: str
    source_id: str
    title: str
    snippet: str
    published_at: str | None
    score: float  # 0.0 - 1.0
    matched_terms: list[str] = field(default_factory=list)
    source_url: str = ""


def normalize_term(term: str) -> str:
    """Normalize a search term: lowercase, strip accents, collapse whitespace."""
    term = term.lower().strip()
    nfkd = unicodedata.normalize("NFKD", term)
    term = "".join(c for c in nfkd if not unicodedata.combining(c))
    term = re.sub(r"\s+", " ", term)
    return term


def normalize_text(text: str) -> str:
    """Normalize text for matching."""
    if not text:
        return ""
    text = text.lower()
    nfkd = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in nfkd if not unicodedata.combining(c))
    return text


def metadata_match(
    title: str,
    snippet: str,
    terms: list[str],
    url: str = "",
) -> tuple[float, list[str]]:
    """Score a candidate based on term matches in title + snippet + URL slug.

    Returns (score, matched_terms).
    Score: title match = 2 pts, snippet match = 1 pt, URL slug = 1 pt,
    normalized to 0-1.
    """
    if not terms:
        return 0.0, []

    norm_title = normalize_text(title or "")
    norm_snippet = normalize_text(snippet or "")

    norm_url = ""
    if url:
        path = urlparse(url).path
        norm_url = normalize_text(
            path.replace("-", " ").replace("_", " ").replace("/", " ")
        )

    matched: list[str] = []
    raw_score = 0.0
    max_possible = len(terms) * 4  # max 2 (title) + 1 (snippet) + 1 (url) per term

    for term in terms:
        norm_term = normalize_term(term)
        if not norm_term:
            continue

        in_title = norm_term in norm_title
        in_snippet = norm_term in norm_snippet
        in_url = norm_url and norm_term in norm_url

        if in_title or in_snippet or in_url:
            if term not in matched:
                matched.append(term)

        if in_title:
            raw_score += 2.0
        if in_snippet:
            raw_score += 1.0
        if in_url:
            raw_score += 1.0

    score = min(raw_score / max_possible, 1.0) if max_possible > 0 else 0.0
    return score, matched


def rank_candidates(
    candidates: list[MatchResult],
    topk: int = 5,
) -> list[MatchResult]:
    """Rank candidates by score descending, return top K."""
    sorted_candidates = sorted(candidates, key=lambda c: c.score, reverse=True)
    return [c for c in sorted_candidates[:topk] if c.score > 0]
