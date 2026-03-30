"""Domain ports — abstract interfaces (Protocols) for infrastructure adapters."""

from newsradar_server.domain.ports.protocols import (
    ClassifierService,
    ContentFetcher,
    DocumentRepository,
    NotificationService,
    ScoringService,
    SearchProvider,
    SourceRepository,
    TextExtractor,
)

__all__ = [
    "ClassifierService",
    "ContentFetcher",
    "DocumentRepository",
    "NotificationService",
    "ScoringService",
    "SearchProvider",
    "SourceRepository",
    "TextExtractor",
]
