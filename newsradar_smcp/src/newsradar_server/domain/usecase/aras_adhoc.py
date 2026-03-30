"""Use case: ARAS ad-hoc query.

Executes an ad-hoc news search for a specific company (by name or NIT),
classifies results by ARAS category, assigns severity, extracts evidence,
and exports to Excel.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ArasAdhocUseCase:
    """Orchestrates the ARAS ad-hoc pipeline.

    Parameters
    ----------
    classifier : Any
        ClassifierService adapter (RulesClassifier or LLMClassifier).
    severity_scorer : Any
        SeverityScorer adapter.
    evidence_extractor : Any
        EvidenceExtractor adapter.
    excel_exporter : Any
        ExcelExporter adapter.
    nit_resolver : Any
        NITResolver adapter.
    output_dir : str
        Directory for Excel output files.
    """

    def __init__(
        self,
        classifier: Any = None,
        severity_scorer: Any = None,
        evidence_extractor: Any = None,
        excel_exporter: Any = None,
        nit_resolver: Any = None,
        output_dir: str = "output/aras",
    ) -> None:
        self._classifier = classifier
        self._severity_scorer = severity_scorer
        self._evidence_extractor = evidence_extractor
        self._excel_exporter = excel_exporter
        self._nit_resolver = nit_resolver
        self._output_dir = output_dir

    def execute(
        self,
        *,
        company: str | None = None,
        nit: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        classifier_mode: str = "rules",
    ) -> dict[str, Any]:
        """Run an ARAS ad-hoc query.

        Steps:
        1. Resolve NIT → company name (if NIT provided)
        2. Search news for company
        3. Classify each document by ARAS category
        4. Assign severity + extract evidence
        5. Export results to Excel

        Returns
        -------
        dict
            Keys: run_id, company, total_documents, total_classified,
            excel_path, results (list of doc summaries).
        """
        run_id = str(uuid.uuid4())[:8]

        # Step 1: Resolve NIT if provided
        resolved_company = company
        if nit and not company:
            if self._nit_resolver is not None:
                resolved = self._nit_resolver.resolve(nit)
                if resolved is None:
                    return {
                        "run_id": run_id,
                        "error": f"NIT {nit} no encontrado",
                        "total_documents": 0,
                    }
                resolved_company = resolved.get("name", nit) if isinstance(resolved, dict) else resolved
            else:
                logger.warning("NITResolver not configured, using NIT as company: %s", nit)
                resolved_company = nit

        if not resolved_company:
            return {"run_id": run_id, "error": "company or nit required", "total_documents": 0}

        # TODO: Step 2 — Search news via pipeline (fetch + discover)
        # For now, this is a placeholder; full pipeline integration pending
        documents: list[Any] = []
        logger.info("ARAS ad-hoc search for company=%s, run_id=%s", resolved_company, run_id)

        # TODO: Step 3 — Classify each document
        # TODO: Step 4 — Severity + evidence extraction

        classified_count = sum(1 for d in documents if getattr(d, "category", None))

        # Step 5: Export to Excel
        excel_path: str | None = None
        if self._excel_exporter is not None:
            try:
                output_file = Path(self._output_dir) / f"aras_{run_id}.xlsx"
                metadata = {
                    "run_id": run_id,
                    "fecha_ejecución": datetime.now().isoformat(),
                    "empresa_o_términos": resolved_company,
                    "rango_fechas": f"{date_from or ''} - {date_to or ''}",
                    "total_documentos": len(documents),
                    "total_clasificados": classified_count,
                }
                result_path = self._excel_exporter.export(
                    documents=documents,
                    output_path=str(output_file),
                    metadata=metadata,
                )
                excel_path = str(result_path)
                logger.info("Excel exported to %s", excel_path)
            except Exception:
                logger.exception("Failed to export Excel for run %s", run_id)

        return {
            "run_id": run_id,
            "company": resolved_company,
            "total_documents": len(documents),
            "total_classified": classified_count,
            "excel_path": excel_path,
            "results": [],  # TODO: populate with document summaries
        }


# Backward-compatible function alias
def aras_adhoc(
    *,
    company: str | None = None,
    nit: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    classifier_mode: str = "rules",
    config: Any = None,
) -> Any:
    """Run an ARAS ad-hoc query (function wrapper).

    Delegates to ArasAdhocUseCase.execute().
    """
    use_case = ArasAdhocUseCase()
    return use_case.execute(
        company=company,
        nit=nit,
        date_from=date_from,
        date_to=date_to,
        classifier_mode=classifier_mode,
    )
