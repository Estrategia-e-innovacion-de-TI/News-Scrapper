"""Infrastructure pipeline package with lazy imports.

Avoid importing the LangGraph runtime on package import so lightweight helpers
such as ``TrendmapPipeline`` can be used in tests and adapters without the
optional extraction stack being installed.
"""
from __future__ import annotations

from typing import Any

__all__ = [
    "build_graph",
    "compile_graph",
    "run_extraction",
    "TrendmapPipeline",
]


def __getattr__(name: str) -> Any:
    if name == "TrendmapPipeline":
        from .trendmap_pipeline import TrendmapPipeline

        return TrendmapPipeline

    if name in {"build_graph", "compile_graph", "run_extraction"}:
        from .pipeline import build_graph, compile_graph, run_extraction

        return {
            "build_graph": build_graph,
            "compile_graph": compile_graph,
            "run_extraction": run_extraction,
        }[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
