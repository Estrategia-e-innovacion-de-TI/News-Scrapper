"""Export adapters — ExcelExporter and PowerBIExporter.

ExcelExporter: generates .xlsx with openpyxl for ad-hoc queries.
PowerBIExporter: generates structured JSON for Power BI dashboards.
"""
from __future__ import annotations

from typing import Any

from newsradar_server.domain.model.entities import Document


class ExcelExporter:
    """Generates Excel (.xlsx) files for ad-hoc query results.

    Sheets: "Resultados" (documents) and "Metadata" (run info).
    Auto-adjusts column widths (max 80 chars).

    Implements: export_excel capability.
    """

    def export(
        self,
        documents: list[Document],
        output_path: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Export documents to Excel.

        TODO: Port implementation from extractor/capabilities/excel_exporter.py
        """
        raise NotImplementedError("TODO: port ExcelExporter from extractor")


class PowerBIExporter:
    """Generates Power BI JSON for historical analysis dashboards.

    Schema: {meta, clusters, trend_timeline, hype_indicators, top_items}.
    Validates against POWERBI_SCHEMA before writing.

    Implements: export_powerbi_json capability.
    """

    def export(
        self,
        clusters: list[dict[str, Any]],
        trend_timeline: list[dict[str, Any]],
        hype_indicators: list[dict[str, Any]],
        output_path: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Export clustering results to Power BI JSON.

        TODO: Port implementation from extractor/capabilities/powerbi_exporter.py
        """
        raise NotImplementedError("TODO: port PowerBIExporter from extractor")
