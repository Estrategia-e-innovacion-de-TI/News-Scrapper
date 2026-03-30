"""Protocol definitions for domain ports.

These define the contracts that infrastructure adapters must implement.
The domain layer depends only on these protocols, never on concrete
implementations.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from newsradar_server.domain.model.entities import (
    Document,
    EvidenceSpan,
    SourceConfig,
)


# ── Classification ───────────────────────────────────────────────────


@runtime_checkable
class ClassifierService(Protocol):
    """Classifies a document by ARAS category or risk type."""

    def classify(
        self,
        text: str,
        title: str,
        query_type: str,
        categories: list[str] | None = None,
    ) -> Any:
        """Return a ClassifyResult with label, confidence, metadata."""
        ...


# ── Scoring ──────────────────────────────────────────────────────────


@runtime_checkable
class ScoringService(Protocol):
    """Assigns severity or relevance score to a document."""

    def score_severity(
        self, doc: Document, classify_result: Any
    ) -> Any:
        """Return a SeverityResult with severity, confidence, evidence_spans."""
        ...

    def score_relevance(
        self, doc: Document, query_terms: list[str]
    ) -> int:
        """Return a relevance score 0..100."""
        ...


# ── Content Fetching ─────────────────────────────────────────────────


@runtime_checkable
class ContentFetcher(Protocol):
    """Fetches raw content from a URL."""

    def fetch(self, url: str, **kwargs: Any) -> str:
        """Return the raw content (HTML/text) from the URL."""
        ...


# ── Text Extraction ──────────────────────────────────────────────────


@runtime_checkable
class TextExtractor(Protocol):
    """Extracts clean text from raw HTML/content."""

    def extract(self, raw_content: str, url: str) -> str:
        """Return cleaned text from raw content."""
        ...


# ── Persistence ──────────────────────────────────────────────────────


@runtime_checkable
class DocumentRepository(Protocol):
    """Persists and retrieves documents."""

    def save(self, documents: list[Document]) -> int:
        """Save documents, return count of saved."""
        ...

    def find_by_hash(self, hash_value: str) -> Document | None:
        """Find a document by its content hash."""
        ...


@runtime_checkable
class SourceRepository(Protocol):
    """Manages source configurations."""

    def load_sources(self, catalog_path: str) -> list[SourceConfig]:
        """Load source configs from catalog."""
        ...

    def get_source(self, source_id: str) -> SourceConfig | None:
        """Get a single source by ID."""
        ...


# ── Search ───────────────────────────────────────────────────────────


@runtime_checkable
class SearchProvider(Protocol):
    """Provides search capabilities (ArXiv, GitHub, Patents, etc.)."""

    def search(
        self, query: str, mode: str, **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Execute a search and return results."""
        ...


# ── Notifications ────────────────────────────────────────────────────


@runtime_checkable
class NotificationService(Protocol):
    """Sends notifications (email, SNS, etc.)."""

    def notify(
        self, subject: str, body: str, recipients: list[str]
    ) -> bool:
        """Send a notification. Return True on success."""
        ...
