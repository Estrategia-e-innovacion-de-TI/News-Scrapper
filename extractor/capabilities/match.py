"""Capability: metadata-only term matching.

Wraps extractor.adhoc.match for reuse as a standalone capability.
"""
from __future__ import annotations

from ..adhoc.match import metadata_match, normalize_term, normalize_text
from .registry import CapabilityDef, register_capability


def match_terms_metadata_only(
    title: str,
    snippet: str,
    terms: list[str],
) -> dict:
    """Match terms against title/snippet metadata.

    Returns dict with score (0-1) and matched_terms list.
    """
    score, matched = metadata_match(title, snippet, terms)
    return {"score": score, "matched_terms": matched}


# Register capability
_cap = CapabilityDef(
    name="match_terms",
    purpose="Match terms against title/snippet metadata (fast, no fetch)",
    inputs_schema={"title": "str", "snippet": "str", "terms": "list[str]"},
    outputs_schema={"score": "float", "matched_terms": "list[str]"},
    callable=match_terms_metadata_only,
    tags=["matching", "metadata", "adhoc"],
)
register_capability(_cap)

# Re-export for convenience
__all__ = ["match_terms_metadata_only", "normalize_text", "normalize_term"]
