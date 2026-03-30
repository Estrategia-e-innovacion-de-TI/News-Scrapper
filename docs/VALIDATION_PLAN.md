# VALIDATION PLAN — News Radar MVP

**Fecha:** 2026-03-16  
**Objetivo:** Checklist paso a paso para validar el estado actual del repo y los gaps respecto a la especificación.

---

## 1. Inventario del Repo

### 1.1 Módulos Core

| Módulo | Archivo | Estado | Tests |
|--------|---------|--------|-------|
| CLI Entry Point | `extractor/main.py` | ✅ Implementado | Validación manual |
| LangGraph Pipeline | `extractor/graph.py` | ✅ 8 nodos | Integración |
| State Models | `extractor/state.py` | ✅ Pydantic v2 | test_provenance_fields (4) |
| Catalog Loader | `extractor/catalog.py` | ✅ YAML parser | test_catalog_filter (5) |
| Report Generator | `extractor/report.py` | ✅ JSONL + JSON | test_adhoc_report (5) |
| Scheduler | `extractor/scheduler.py` | ✅ SimpleScheduler | Sin tests |
| Utilities | `extractor/utils.py` | ✅ Rate limiter, normalize, detect_language | test_url_normalize (12) |

### 1.2 Conectores

| Conector | Archivo | Estado | Notas |
|----------|---------|--------|-------|
| RSS | `connectors/rss.py` | ✅ feedparser + httpx | SSL tolerant |
| Scrape | `connectors/scrape.py` | ✅ httpx + heurísticas | Selectores CSS |
| Browser | `connectors/browser.py` | ✅ Playwright | Opcional |
| PDF | `connectors/pdf.py` | ✅ PyPDF2 | Download + extract |

### 1.3 Extractores

| Extractor | Archivo | Estado | Tests |
|-----------|---------|--------|-------|
| Text | `extract/text.py` | ✅ trafilatura → readability → bs4 | test_extract_text_fixture (9) |
| Metadata | `extract/metadata.py` | ✅ canonical, title, date, author, JSON-LD | Indirecto |
| Dedupe | `extract/dedupe.py` | ✅ SHA256 hash | test_dedupe (7) |
| Normalize | `extract/normalize.py` | ✅ URL + whitespace + title | test_url_normalize (12) |

### 1.4 Ad-Hoc

| Módulo | Archivo | Estado | Tests |
|--------|---------|--------|-------|
| ARAS Filter | `adhoc/aras.py` | ✅ company_to_terms, filter, build | test_adhoc_aras_company_query (4) |
| Riesgos Filter | `adhoc/riesgos.py` | ✅ parse_terms, filter, build | test_adhoc_riesgos_terms_query (4) |
| Match Engine | `adhoc/match.py` | ✅ metadata_match, rank_candidates | test_adhoc_match_metadata_only (7) |
| Date Range | adhoc/aras.py (_in_date_range) | ✅ Implementado | test_date_range_filter (11) |

### 1.5 Search Agent

| Módulo | Archivo | Estado | Tests |
|--------|---------|--------|-------|
| Orchestrator | `search/orchestrator.py` | ✅ run_search | Indirecto |
| ArXiv Provider | `search/providers/arxiv.py` | ✅ Atom RSS | test_search_terms_loader (5) |
| GitHub Provider | `search/providers/github.py` | ✅ REST API v3 | Indirecto |
| Google Patents | `search/providers/google_patents.py` | ⚠️ Limitado (SPA/CAPTCHA) | Indirecto |
| Filters | `search/filters.py` | ✅ repos, papers, patents | Indirecto |
| Terms Loader | `search/loader.py` | ✅ YAML | test_search_terms_loader (5) |
| Export | `search/export.py` | ✅ JSONL + report | Indirecto |
| Models | `search/models.py` | ✅ SearchCandidate, SearchReport | Indirecto |

### 1.6 Ops

| Módulo | Archivo | Estado | Tests |
|--------|---------|--------|-------|
| Tiering | `ops/tiering.py` | ✅ classify_sources, build_prod_set | test_tiering (9) |
| Catalog Filter | `ops/catalog_filter.py` | ✅ write_filtered, write_prod, write_tiers | test_catalog_filter (5) |
| Ops CLI | `ops/__main__.py` | ✅ tier + diagnose-tier2 | Manual |

### 1.7 Skills

| Módulo | Archivo | Estado | Tests |
|--------|---------|--------|-------|
| Registry | `skills/registry.py` | ✅ SkillDef, register, get, list | Indirecto |
| Match | `skills/match.py` | ✅ match_terms_metadata_only | test_skills_match |
| Classify | `skills/classify.py` | 🔲 Placeholder | Sin tests |
| Ranking | `skills/ranking.py` | 🔲 Placeholder | Sin tests |

### 1.8 Source Evaluator

| Módulo | Archivo | Estado | Tests |
|--------|---------|--------|-------|
| Discover | `source_eval/discover.py` | ✅ feeds, paywall, JS detection | Indirecto |
| Evaluator | `source_eval/evaluator.py` | ✅ news + non-news evaluation | Indirecto |
| Selectors | `source_eval/selectors.py` | ✅ listing + article selectors | Indirecto |
| Outputs | `source_eval/outputs.py` | ✅ catalog_patch + scorecard | test_source_eval_outputs_patch (5) |

### 1.9 Playbooks (Skills-Docs)

| Playbook | Archivo | Estado |
|----------|---------|--------|
| ARAS Ad-Hoc | `playbooks/ARAS_ADHOC.md` | ✅ Completo |
| Riesgos Ad-Hoc | `playbooks/RIESGOS_ADHOC.md` | ✅ Completo |
| Vigilancia Tech | `playbooks/VIGILANCIA_TECH.md` | ✅ Completo |
| Source Onboarding | `playbooks/SOURCE_ONBOARDING.md` | ✅ Completo |

### 1.10 Datos y Configuración

| Archivo | Estado | Notas |
|---------|--------|-------|
| `catalog.yaml` | ✅ 37 fuentes | 3 pipelines: vigilancia_global, aras_latam, riesgos_latam |
| `catalog_patch.yaml` | ✅ Patches generados | 37 fuentes perfiladas |
| `source_profiles.json` | ✅ Resumen de perfilado | 8 RSS, 15 Playwright, 5 paywall |
| `terms_vigilancia.yaml` | ✅ papers/repos/patents | 5+4+3 términos |

### 1.11 Tests

| Test File | Count | Área |
|-----------|-------|------|
| test_adhoc_match_metadata_only | 7 | Matching |
| test_adhoc_aras_company_query | 4 | ARAS |
| test_adhoc_riesgos_terms_query | 4 | Riesgos |
| test_adhoc_counts | ? | Adhoc counts |
| test_adhoc_params_validation | ? | Params validation |
| test_adhoc_report | ? | Report generation |
| test_date_range_filter | 11 | Date filtering |
| test_search_terms_loader | 5 | Search terms |
| test_source_eval_outputs_patch | 5 | Source eval |
| test_tiering | 9 | Tiering |
| test_catalog_filter | 5 | Catalog filter |
| test_dedupe | 7 | Deduplication |
| test_extract_text_fixture | 9 | Text extraction |
| test_url_normalize | 12 | URL normalize |
| test_provenance_fields | 4 | Provenance |
| test_skills_match | ? | Skills match |
| **TOTAL** | **93+** | |

---

## 2. Checklist de Validación por Requisito

### REQ-1: ARAS Ad-Hoc

- [x] CLI flags: --focus aras_news --adhoc --company --date-from --date-to
- [x] Validación de combinaciones (validate_args)
- [x] Descubrimiento de items (RSS/scrape)
- [x] Filtrado por rango de fechas (_in_date_range)
- [x] Matching metadata-only (metadata_match)
- [x] Top-K por fuente + Top-K global
- [x] Fetch completo de candidatos
- [x] Deduplicación por hash
- [x] Provenance fields (origin, query_type, query_terms, query_range)
- [ ] **GAP: Resolución NIT → nombre de empresa**
- [ ] **GAP: Clasificación LLM por categoría ARAS**
- [ ] **GAP: Severidad H/M/L con confianza**
- [ ] **GAP: Evidencia (citas textuales)**
- [ ] **GAP: Generación de Excel**

### REQ-2: Riesgos Emergentes Ad-Hoc

- [x] CLI flags: --focus riesgos_news --adhoc --terms --date-from --date-to
- [x] Parse de términos comma-separated
- [x] Filtrado por rango de fechas
- [x] Matching metadata-only
- [x] Top-K por fuente + Top-K global
- [x] Fetch + deduplicación + provenance
- [ ] **GAP: Clasificación LLM por tipo de riesgo**
- [ ] **GAP: Detección de eventos materializados**
- [ ] **GAP: Severidad H/M/L**
- [ ] **GAP: Evidencia (citas)**
- [ ] **GAP: Excel output**
- [ ] **GAP: Presets de términos (ciber|fraude|operacional|all)**

### REQ-3: Trazabilidad y Auditoría

- [x] run_id único por ejecución
- [x] run_report.json con parámetros y métricas
- [x] Provenance en Document (origin, query_type, query_terms, query_range)
- [x] Error tracking con error_type tipificado (ErrorType enum)
- [x] adhoc_summary en run_report (parcial)
- [ ] **GAP: evidence_spans en documentos con severidad H/M**
- [ ] **GAP: candidates_evaluated/matched/fetched en adhoc_summary**

### REQ-4: Vigilancia — Boletín Semanal

- [x] --focus vigilancia_news --days 7
- [x] Extracción de fuentes con focus vigilancia_global
- [ ] **GAP: Filtrado por query_groups del suscriptor**
- [ ] **GAP: Scoring 0..100 con rúbrica configurable**
- [ ] **GAP: Top-10 con diversidad de fuentes**
- [ ] **GAP: Resumen ejecutivo Markdown/HTML**
- [ ] **GAP: Envío por email**

### REQ-5: Vigilancia — Análisis Histórico

- [x] Search papers (ArXiv)
- [x] Search repos (GitHub)
- [x] Search patents (Google Patents, limitado)
- [x] Ingesta de candidates.jsonl
- [ ] **GAP: Clustering TF-IDF**
- [ ] **GAP: Trend mapping temporal**
- [ ] **GAP: Novelty scoring**
- [ ] **GAP: JSON para Power BI**
- [ ] **GAP: Reportes anuales**

### REQ-6: Términos de Vigilancia

- [x] terms_vigilancia.yaml con papers/repos/patents
- [x] Loader YAML funcional
- [ ] **GAP: Sección news en terms_vigilancia.yaml**
- [ ] **GAP: Términos ES + EN con aliases**
- [ ] **GAP: query_groups temáticos**

### REQ-7: Volumen y Rendimiento

- [x] topk_per_source configurable
- [x] max_candidates_total configurable
- [x] max_items_per_source configurable
- [x] max_text_chars configurable
- [x] Rate limiting por fuente
- [x] Timeout configurable
- [ ] **GAP: Benchmark de tiempo < 5 min para 50 candidatos**

### REQ-8: Políticas de Matching

- [x] Normalización (lowercase, strip accents, collapse whitespace)
- [x] Scoring (título 2pts, snippet 1pt, URL slug 1pt)
- [x] Filtro score > 0
- [x] Penalización sin published_at (×0.7)
- [x] Deduplicación SHA256

### REQ-9: Skills

- [x] Registry con SkillDef
- [x] Playbooks en playbooks/
- [x] match.py con contrato
- [ ] **GAP: classify.py es placeholder**
- [ ] **GAP: ranking.py es placeholder**
- [ ] **GAP: Validación de callable en registro**

### REQ-10: Clean Architecture

- [ ] **GAP: Todo el código está en estructura plana extractor/**
- [ ] **GAP: No hay separación domain/application/infrastructure/interfaces**
- [ ] **GAP: No hay interfaces/protocolos definidos**
- [ ] **GAP: Imports directos entre capas**

### REQ-11: AWS SBX

- [ ] **GAP: No hay IaC (CDK/SAM/Terraform)**
- [ ] **GAP: No hay configuración de Lambda/Fargate**
- [ ] **GAP: No hay integración S3**
- [ ] **GAP: No hay Secrets Manager**
- [ ] **GAP: No hay notificaciones SNS**

### REQ-12: Excel Output

- [ ] **GAP: No hay generación de Excel**
- [ ] **GAP: No hay dependencia openpyxl/xlsxwriter**

---

## 3. Resumen de Gaps

| ID | Gap | Severidad | Requisito |
|----|-----|-----------|-----------|
| G01 | Clasificación LLM (ARAS + Riesgos) | Alta | REQ-1, REQ-2 |
| G02 | Severidad H/M/L con evidencia | Alta | REQ-1, REQ-2 |
| G03 | Excel output | Alta | REQ-1, REQ-2, REQ-12 |
| G04 | Scoring 0..100 vigilancia | Alta | REQ-4 |
| G05 | Clustering + trends + Power BI JSON | Media | REQ-5 |
| G06 | Suscripciones por usuario/tema | Media | REQ-4 |
| G07 | Resolución NIT | Media | REQ-1 |
| G08 | Presets de términos riesgos | Baja | REQ-2 |
| G09 | query_groups ES+EN | Media | REQ-6 |
| G10 | Clean Architecture migration | Media | REQ-10 |
| G11 | AWS SBX deployment | Media | REQ-11 |
| G12 | Newsletter HTML/email | Baja | REQ-4 |
| G13 | Google Patents confiable | Baja | REQ-5 |
| G14 | Evidence spans | Media | REQ-3 |
| G15 | Detección eventos materializados | Media | REQ-2 |
