"""Use case: Extract news from configured sources.

Orchestrates the full pipeline: load catalog → select sources → discover
items → fetch content → classify/score → persist.
"""
from __future__ import annotations

from typing import Any

# TODO: Implement extract_news use case
# This should coordinate the pipeline steps using injected ports:
# - SourceRepository to load catalog
# - ContentFetcher to fetch content
# - TextExtractor to extract text
# - ClassifierService to classify documents
# - ScoringService to score documents
# - DocumentRepository to persist results


def extract_news(*, config: Any) -> Any:
    """Run the full news extraction pipeline.

    Parameters
    ----------
    config : Any
        Pipeline configuration (catalog path, focus, days, etc.)

    Returns
    -------
    Any
        Run metrics and results summary.
    """
    raise NotImplementedError("TODO: wire up extract_news use case")
