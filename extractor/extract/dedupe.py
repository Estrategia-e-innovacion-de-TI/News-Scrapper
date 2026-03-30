"""Hash-based deduplication for documents."""
from __future__ import annotations

import hashlib
import logging
from typing import Set

from ..extract.normalize import normalize_title, normalize_whitespace

logger = logging.getLogger("news_radar.dedupe")


def compute_content_hash(title: str, text: str, max_text_len: int = 2000) -> str:
    """
    Compute SHA256 hash for deduplication.
    Uses normalized title + first N chars of normalized text.
    """
    norm_title = normalize_title(title or "")
    norm_text = normalize_whitespace(text or "")[:max_text_len]
    
    content = f"{norm_title}|{norm_text}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class Deduplicator:
    """Hash-based deduplication within a run."""
    
    def __init__(self):
        self._seen: Set[str] = set()
    
    def is_duplicate(self, content_hash: str) -> bool:
        """Check if hash has been seen."""
        return content_hash in self._seen
    
    def add(self, content_hash: str) -> bool:
        """
        Add hash to seen set.
        Returns True if new, False if duplicate.
        """
        if content_hash in self._seen:
            return False
        self._seen.add(content_hash)
        return True
    
    def check_and_add(self, title: str, text: str) -> tuple[str, bool]:
        """
        Compute hash and check/add in one step.
        Returns (hash, is_new).
        """
        content_hash = compute_content_hash(title, text)
        is_new = self.add(content_hash)
        return content_hash, is_new
    
    @property
    def count(self) -> int:
        """Number of unique items seen."""
        return len(self._seen)
    
    def clear(self):
        """Clear seen hashes."""
        self._seen.clear()
