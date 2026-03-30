"""Use case: Vigilancia historical analysis.

Executes historical analysis: fetch papers/repos/patents, cluster by
TF-IDF similarity, compute trend timelines and hype indicators,
export Power BI JSON.
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class VigilanciaHistoricalUseCase:
    """Orchestrates the historical vigilancia analysis pipeline.

    Parameters
    ----------
    cluster_engine : Any
        ClusterEngine adapter for TF-IDF clustering.
    powerbi_exporter : Any
        PowerBIExporter adapter for JSON output.
    output_dir : str
        Directory for Power BI JSON output files.
    """

    def __init__(
        self,
        cluster_engine: Any = None,
        powerbi_exporter: Any = None,
        output_dir: str = "output/vigilancia/historical",
    ) -> None:
        self._cluster_engine = cluster_engine
        self._powerbi_exporter = powerbi_exporter
        self._output_dir = output_dir

    def execute(
        self,
        *,
        modes: list[str] | None = None,
        period: str = "",
    ) -> dict[str, Any]:
        """Run the historical vigilancia analysis.

        Steps:
        1. Fetch items (papers/repos/patents) — TODO: wire to pipeline
        2. Cluster items via ClusterEngine
        3. Export clustering results to Power BI JSON via PowerBIExporter

        Returns
        -------
        dict
            Keys: run_id, total_items, total_clusters, powerbi_path.
        """
        run_id = str(uuid.uuid4())[:8]
        logger.info(
            "Vigilancia historical analysis: run_id=%s, modes=%s",
            run_id, modes,
        )

        # Step 1: Fetch items from pipeline
        # TODO: Wire to extract_news pipeline for papers/repos/patents
        items: list[dict[str, Any]] = []

        # Step 2: Cluster items
        clustering_output = None
        if self._cluster_engine is not None:
            try:
                clustering_output = self._cluster_engine.cluster(items)
                logger.info(
                    "Clustering complete: %d clusters",
                    len(clustering_output.clusters) if clustering_output else 0,
                )
            except Exception:
                logger.exception("Clustering failed for run %s", run_id)

        # Step 3: Export to Power BI JSON
        powerbi_path: str | None = None
        if self._powerbi_exporter is not None and clustering_output is not None:
            try:
                out_file = self._powerbi_exporter.export(
                    clustering_output=clustering_output,
                    out_dir=str(Path(self._output_dir) / run_id),
                    period=period,
                    modes=modes,
                )
                powerbi_path = str(out_file)
                logger.info("Power BI JSON exported to %s", powerbi_path)
            except Exception:
                logger.exception("Power BI export failed for run %s", run_id)

        total_clusters = (
            len(clustering_output.clusters) if clustering_output else 0
        )

        return {
            "run_id": run_id,
            "total_items": len(items),
            "total_clusters": total_clusters,
            "powerbi_path": powerbi_path,
        }


# Backward-compatible function alias
def vigilancia_historical(*, config: Any = None) -> Any:
    """Run the historical vigilancia analysis (function wrapper).

    Delegates to VigilanciaHistoricalUseCase.execute().
    """
    use_case = VigilanciaHistoricalUseCase()
    modes = config.get("modes") if isinstance(config, dict) else None
    period = config.get("period", "") if isinstance(config, dict) else ""
    return use_case.execute(modes=modes, period=period)
