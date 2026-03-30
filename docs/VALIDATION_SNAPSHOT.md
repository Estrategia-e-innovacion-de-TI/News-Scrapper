# Validation Snapshot

Fecha: 2026-03-16

## Capacidades Existentes

| Capacidad | Estado | Ubicación |
|-----------|--------|-----------|
| Extracción general (catalog → JSONL) | ✅ Implementado | `extractor/graph.py`, `extractor/main.py` |
| `--focus` (aras_news, riesgos_news, vigilancia_news) | ✅ Implementado | `extractor/main.py` |
| `--adhoc` modo ad-hoc | ✅ Implementado | `extractor/main.py`, `extractor/graph.py` |
| ARAS ad-hoc (company + rango) | ✅ Implementado | `extractor/adhoc/aras.py` |
| Riesgos ad-hoc (terms + rango) | ✅ Implementado | `extractor/adhoc/riesgos.py` |
| Metadata-only matching (Opción 1) | ✅ Implementado | `extractor/adhoc/match.py` |
| Date range filtering (date_from/date_to) | ✅ Implementado | `extractor/adhoc/aras.py`, `extractor/adhoc/riesgos.py` |
| `--candidates` ingesta desde JSONL | ✅ Implementado | `extractor/graph.py` |
| Search papers (ArXiv) | ✅ Implementado | `extractor/search/providers/arxiv.py` |
| Search repos (GitHub) | ✅ Implementado | `extractor/search/providers/github.py` |
| Search patents (Google Patents SERP) | ⚠️ Limitado (SPA) | `extractor/search/providers/google_patents.py` |
| Source Evaluator | ✅ Implementado | `extractor/source_eval/` |
| Tiering (Tier0/1/2) | ✅ Implementado | `extractor/ops/tiering.py` |
| Prod Mode B | ✅ Implementado | `extractor/ops/catalog_filter.py` |
| Error tipificación (timeout, 403, 4xx, 5xx, etc.) | ✅ Implementado | `extractor/state.py` (ErrorType enum) |
| SkipReason separado de ErrorType | ✅ Implementado | `extractor/state.py` (SkipReason enum) |
| Text cap (max_text_chars) | ✅ Implementado | `extractor/graph.py` (`_process_html`) |
| Provenance fields (origin, query_type, query_terms, query_range) | ✅ Implementado | `extractor/state.py` (Document), `extractor/graph.py` |
| Adhoc summary en report | ✅ Implementado | `extractor/report.py` |
| RSS connector (SSL tolerant) | ✅ Implementado | `extractor/connectors/rss.py` |
| Playwright connector | ✅ Implementado | `extractor/connectors/browser.py` |
| PDF connector | ✅ Implementado | `extractor/connectors/pdf.py` |
| Deduplicación por hash | ✅ Implementado | `extractor/extract/dedupe.py` |

## Gaps Identificados

| Gap | Severidad | Notas |
|-----|-----------|-------|
| Google Patents devuelve 0 resultados (SPA/CAPTCHA) | Media | Requiere SerpAPI o Playwright para resultados confiables |
| No hay alias automáticos de empresa | Baja | Fuera de alcance por diseño |
| No hay LLM-based matching | Baja | Fase futura; metadata-only es suficiente para MVP |
| Skills-Code framework | Media | Implementado como `extractor/skills/` |
| Playbooks (Skills-Docs) | Media | Implementado en `playbooks/` |

## Tests

- 93 tests pasando (pytest)
- Cobertura: adhoc match, ARAS, Riesgos, tiering, dedupe, URL normalize, search loader, source eval outputs, catalog filter, text extraction
