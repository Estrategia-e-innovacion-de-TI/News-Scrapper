"""Capabilities: Reusable pipeline functions with defined contracts.

Each capability is a callable function with:
- name: identifier
- purpose: what it does
- inputs_schema: expected inputs
- outputs_schema: expected outputs
- callable: the function itself
"""
from .registry import CAPABILITY_REGISTRY, get_capability, list_capabilities
from .match import match_terms_metadata_only, normalize_text
from .ranking import rank_items  # noqa: F401 — registers capability
from .classify import classify_document  # noqa: F401 — registers capability
from .excel_export import export_excel  # noqa: F401 — registers capability
from .nit_resolver import resolve_nit, NITResolver, NITResult  # noqa: F401 — registers capability
from .clustering import ClusterEngine, ClusteringOutput, ClusterResult, TrendEntry, HypeIndicator  # noqa: F401 — registers capability
from .powerbi_export import PowerBIExporter, export_powerbi_json, POWERBI_SCHEMA  # noqa: F401 — registers capability
from .subscription import SubscriptionManager, Subscriber  # noqa: F401 — registers capability

__all__ = [
    "CAPABILITY_REGISTRY",
    "get_capability",
    "list_capabilities",
    "match_terms_metadata_only",
    "normalize_text",
    "rank_items",
    "classify_document",
    "export_excel",
    "resolve_nit",
    "NITResolver",
    "NITResult",
    "ClusterEngine",
    "ClusteringOutput",
    "ClusterResult",
    "TrendEntry",
    "HypeIndicator",
    "PowerBIExporter",
    "export_powerbi_json",
    "POWERBI_SCHEMA",
    "SubscriptionManager",
    "Subscriber",
]
