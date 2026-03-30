"""Capability: evidence extraction from document text.

EvidenceExtractor extracts up to N text fragments (default 3) of ±window
characters (default 150) around each matched term in the document text.

Key improvements over the basic ``SeverityScorer._build_evidence_spans``:
  - Highlights matched terms with square brackets: ``[término]``
  - Properly merges overlapping spans into a single span
  - Adds ``...`` prefix/suffix when the span doesn't start/end at the
    document boundary
  - Can be used independently from SeverityScorer
"""
from __future__ import annotations

import logging
import re
from typing import Sequence

from ..adhoc.match import normalize_text
from ..state import EvidenceSpan

logger = logging.getLogger(__name__)


class EvidenceExtractor:
    """Extracts highlighted evidence spans around matched terms."""

    def extract(
        self,
        text: str,
        matched_terms: list[str],
        max_spans: int = 3,
        window: int = 150,
    ) -> list[EvidenceSpan]:
        """Extract evidence spans from *text* around *matched_terms*.

        Parameters
        ----------
        text:
            Full document text (original casing preserved).
        matched_terms:
            Terms that were matched in the document.
        max_spans:
            Maximum number of evidence spans to return.
        window:
            Number of characters on each side of the matched term.

        Returns
        -------
        list[EvidenceSpan]
            Up to *max_spans* evidence spans with highlighted terms.
        """
        if not text or not matched_terms or max_spans <= 0:
            return []

        norm_text = normalize_text(text)

        # 1. Find all occurrences of each term in the normalized text
        raw_hits: list[tuple[int, int, str]] = []  # (start, end, original_term)
        for term in matched_terms:
            norm_term = normalize_text(term)
            if not norm_term:
                continue
            # Use simple find to locate all occurrences
            search_start = 0
            while True:
                idx = norm_text.find(norm_term, search_start)
                if idx == -1:
                    break
                raw_hits.append((idx, idx + len(norm_term), term))
                search_start = idx + 1

        if not raw_hits:
            return []

        # Sort hits by position
        raw_hits.sort(key=lambda h: h[0])

        # Deduplicate: keep only the first occurrence per term
        seen_terms: set[str] = set()
        unique_hits: list[tuple[int, int, str]] = []
        for start, end, term in raw_hits:
            norm_t = normalize_text(term)
            if norm_t not in seen_terms:
                seen_terms.add(norm_t)
                unique_hits.append((start, end, term))

        # 2. Build windows around each hit
        windows: list[tuple[int, int, str]] = []
        for hit_start, hit_end, term in unique_hits:
            win_start = max(0, hit_start - window)
            win_end = min(len(text), hit_end + window)
            windows.append((win_start, win_end, term))

        # 3. Merge overlapping windows
        merged = self._merge_windows(windows)

        # 4. Limit to max_spans
        merged = merged[:max_spans]

        # 5. Build EvidenceSpan objects with highlighting
        spans: list[EvidenceSpan] = []
        for win_start, win_end, primary_term in merged:
            fragment = text[win_start:win_end]
            highlighted = self._highlight_terms(
                fragment, win_start, text, matched_terms,
            )

            # Add ellipsis markers
            prefix = "..." if win_start > 0 else ""
            suffix = "..." if win_end < len(text) else ""
            highlighted = f"{prefix}{highlighted}{suffix}"

            spans.append(
                EvidenceSpan(
                    text=highlighted,
                    start_offset=win_start,
                    end_offset=win_end,
                    matched_term=primary_term,
                )
            )

        return spans

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_windows(
        windows: list[tuple[int, int, str]],
    ) -> list[tuple[int, int, str]]:
        """Merge overlapping (start, end, term) windows.

        When two windows overlap, the merged window keeps the *primary_term*
        of the first (leftmost) window.
        """
        if not windows:
            return []

        sorted_wins = sorted(windows, key=lambda w: w[0])
        merged: list[tuple[int, int, str]] = [sorted_wins[0]]

        for start, end, term in sorted_wins[1:]:
            prev_start, prev_end, prev_term = merged[-1]
            if start <= prev_end:
                # Overlapping — extend the previous window
                merged[-1] = (prev_start, max(prev_end, end), prev_term)
            else:
                merged.append((start, end, term))

        return merged

    @staticmethod
    def _highlight_terms(
        fragment: str,
        fragment_offset: int,
        full_text: str,
        matched_terms: Sequence[str],
    ) -> str:
        """Highlight all matched terms in *fragment* with square brackets.

        Uses the normalized text to find term positions, then applies
        brackets to the original-cased fragment.
        """
        norm_fragment = normalize_text(fragment)

        # Collect all (start_in_fragment, end_in_fragment, term) hits
        hits: list[tuple[int, int, str]] = []
        for term in matched_terms:
            norm_term = normalize_text(term)
            if not norm_term:
                continue
            search_start = 0
            while True:
                idx = norm_fragment.find(norm_term, search_start)
                if idx == -1:
                    break
                hits.append((idx, idx + len(norm_term), term))
                search_start = idx + 1

        if not hits:
            return fragment

        # Sort by position, then by length descending (prefer longer matches)
        hits.sort(key=lambda h: (h[0], -(h[1] - h[0])))

        # Remove overlapping hits (greedy left-to-right)
        filtered: list[tuple[int, int, str]] = []
        last_end = -1
        for start, end, term in hits:
            if start >= last_end:
                filtered.append((start, end, term))
                last_end = end

        # Build result by inserting brackets (right-to-left to preserve offsets)
        result = list(fragment)
        for start, end, _term in reversed(filtered):
            result.insert(end, "]")
            result.insert(start, "[")

        return "".join(result)
