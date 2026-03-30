"""Use case: Riesgos Emergentes ad-hoc query.

Executes an ad-hoc news search for risk terms (manual or preset),
classifies results by risk type, detects materialized events,
assigns severity, extracts evidence, and exports to Excel.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RiesgosAdhocUseCase:
    """Orchestrates the Riesgos Emergentes ad-hoc pipeline.

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
    output_dir : str
        Directory for Excel output files.
    """

    def __init__(
        self,
        classifier: Any = None,
        severity_scorer: Any = None,
        evidence_extractor: Any = None,
        excel_exporter: Any = None,
        output_dir: str = "output/riesgos",
    ) -> None:
        self._classifier = classifier
        self._severity_scorer = severity_scorer
        self._evidence_extractor = evidence_extractor
        self._excel_exporter = excel_exporter
        self._output_dir = output_dir

    def execute(
        self,
        *,
        terms: list[str] | None = None,
        terms_preset: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        classifier_mode: str = "rules",
    ) -> dict[str, Any]:
        """Run a Riesgos Emergentes ad-hoc query.

        Steps:
        1. Resolve terms from preset (if provided) and merge with manual terms
        2. Search news for resolved terms
        3. Classify each document by risk type + detect materialized events
        4. Assign severity + extract evidence
        5. Export results to Excel

        Returns
        -------
        dict
            Keys: run_id, terms, total_documents, total_classified,
            excel_path, results (list of doc summaries).
        """
        run_id = str(uuid.uuid4())[:8]

        # Step 1: Resolve terms
        resolved_terms = list(terms or [])
        if terms_preset:
            # TODO: Load preset terms from risk_presets.yaml via preset loader
            logger.info("Using terms_preset=%s", terms_preset)

        if not resolved_terms and not terms_preset:
            return {"run_id": run_id, "error": "terms or terms_preset required", "total_documents": 0}

        terms_label = ", ".join(resolved_terms[:5]) if resolved_terms else terms_preset or ""

        # TODO: Step 2 — Search news via pipeline (fetch + discover)
        # For now, this is a placeholder; full pipeline integration pending
        documents: list[Any] = []
        logger.info("Riesgos ad-hoc search for terms=%s, run_id=%s", terms_label, run_id)

        # TODO: Step 3 — Classify each document by risk type
        # TODO: Step 4 — Severity + evidence extraction

        classified_count = sum(1 for d in documents if getattr(d, "risk_type", None))

        # Step 5: Export to Excel
        excel_path: str | None = None
        if self._excel_exporter is not None:
            try:
                output_file = Path(self._output_dir) / f"riesgos_{run_id}.xlsx"
                metadata = {
                    "run_id": run_id,
                    "fecha_ejecución": datetime.now().isoformat(),
                    "empresa_o_términos": terms_label,
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
            "terms": resolved_terms,
            "terms_preset": terms_preset,
            "total_documents": len(documents),
            "total_classified": classified_count,
            "excel_path": excel_path,
            "results": [],  # TODO: populate with document summaries
        }


# Backward-compatible function alias
def riesgos_adhoc(
    *,
    terms: list[str] | None = None,
    terms_preset: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    classifier_mode: str = "rules",
    config: Any = None,
) -> Any:
    """Run a Riesgos Emergentes ad-hoc query (function wrapper).

    Delegates to RiesgosAdhocUseCase.execute().
    """
    use_case = RiesgosAdhocUseCase()
    return use_case.execute(
        terms=terms,
        terms_preset=terms_preset,
        date_from=date_from,
        date_to=date_to,
        classifier_mode=classifier_mode,
    )
