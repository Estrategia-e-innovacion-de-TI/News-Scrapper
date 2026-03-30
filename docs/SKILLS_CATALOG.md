# CATÁLOGO DE SKILLS — News Radar MVP

**Fecha:** 2026-03-16  
**Convención:** Skills-Docs (playbooks .md) vs Skills-Code (funciones Python)  
**Estado:** ✅ = implementado, 🔲 = pendiente

---

## 1. Skills-Docs (Playbooks)

Instrucciones operativas en Markdown para operadores humanos o agentes.

| Playbook | Archivo | Propósito | Estado |
|----------|---------|-----------|--------|
| ARAS Ad-Hoc | `playbooks/ARAS_ADHOC.md` | Ejecutar consulta ARAS por empresa + rango | ✅ |
| Riesgos Ad-Hoc | `playbooks/RIESGOS_ADHOC.md` | Ejecutar consulta Riesgos por términos + rango | ✅ |
| Vigilancia Tech | `playbooks/VIGILANCIA_TECH.md` | Horizontes de ejecución y comandos | ✅ |
| Source Onboarding | `playbooks/SOURCE_ONBOARDING.md` | Evaluar e incorporar nuevas fuentes | ✅ |
| Scoring Rubric | `playbooks/SCORING_RUBRIC.md` | Definición de rúbrica 0..100 | 🔲 |
| Newsletter Setup | `playbooks/NEWSLETTER_SETUP.md` | Configurar suscripciones y envío | 🔲 |
| AWS Deployment | `playbooks/AWS_DEPLOY.md` | Desplegar en AWS SBX | 🔲 |

---

## 2. Skills-Code (Funciones Python)

### 2.1 Core (comunes a todos los procesos)

| Skill | Módulo | Estado | Tests |
|-------|--------|--------|-------|
| `extract_text` | `extract/text.py` | ✅ | 9 tests |
| `extract_metadata` | `extract/metadata.py` | ✅ | Indirecto |
| `normalize_url` | `extract/normalize.py` + `utils.py` | ✅ | 12 tests |
| `detect_language` | `utils.py` | ✅ | Indirecto |
| `dedupe_hash` | `extract/dedupe.py` | ✅ | 7 tests |
| `dedupe_semantic` | Pendiente | 🔲 | — |
| `source_credibility_score` | Pendiente | 🔲 | — |
| `boilerplate_trim` | Pendiente | 🔲 | — |

### 2.2 ARAS

| Skill | Módulo | Estado | Tests |
|-------|--------|--------|-------|
| `aras_query_builder` | `adhoc/aras.py:company_to_terms` | ✅ | 4 tests |
| `aras_match_metadata_only` | `adhoc/match.py:metadata_match` | ✅ | 7 tests |
| `aras_date_range_filter` | `adhoc/aras.py:_in_date_range` | ✅ | 11 tests |
| `aras_category_classifier` | Pendiente (placeholder en `skills/classify.py`) | 🔲 | — |
| `aras_severity_scoring` | Pendiente | 🔲 | — |
| `aras_evidence_spans` | Pendiente | 🔲 | — |
| `aras_nit_resolver` | Pendiente | 🔲 | — |

### 2.3 Riesgos Emergentes

| Skill | Módulo | Estado | Tests |
|-------|--------|--------|-------|
| `risk_query_builder` | `adhoc/riesgos.py:parse_terms` | ✅ | 4 tests |
| `risk_match_metadata_only` | `adhoc/match.py:metadata_match` | ✅ | 7 tests |
| `risk_date_range_filter` | `adhoc/aras.py:_in_date_range` (compartido) | ✅ | 11 tests |
| `risk_type_classifier` | Pendiente | 🔲 | — |
| `event_materialization_detector` | Pendiente | 🔲 | — |
| `risk_severity_scoring` | Pendiente | 🔲 | — |
| `risk_evidence_spans` | Pendiente | 🔲 | — |
| `risk_terms_presets` | Pendiente | 🔲 | — |

### 2.4 Vigilancia Tecnológica

| Skill | Módulo | Estado | Tests |
|-------|--------|--------|-------|
| `search_arxiv` | `search/providers/arxiv.py` | ✅ | 5 tests (indirecto) |
| `search_github` | `search/providers/github.py` | ✅ | Indirecto |
| `search_patents` | `search/providers/google_patents.py` | ⚠️ Limitado | — |
| `search_filters` | `search/filters.py` | ✅ | Indirecto |
| `search_terms_loader` | `search/loader.py` | ✅ | 5 tests |
| `tech_topic_classifier` | Pendiente | 🔲 | — |
| `relevance_scoring_0_100` | Pendiente | 🔲 | — |
| `topk_ranker` | Pendiente (placeholder en `skills/ranking.py`) | 🔲 | — |
| `trend_cluster` | Pendiente | 🔲 | — |
| `novelty_score` | Pendiente | 🔲 | — |
| `hype_cycle_indicator` | Pendiente | 🔲 | — |

### 2.5 Operaciones

| Skill | Módulo | Estado | Tests |
|-------|--------|--------|-------|
| `classify_sources_tiering` | `ops/tiering.py:classify_sources` | ✅ | 9 tests |
| `build_prod_set` | `ops/tiering.py:build_prod_set` | ✅ | 5 tests |
| `write_filtered_catalog` | `ops/catalog_filter.py` | ✅ | 5 tests |
| `evaluate_source` | `source_eval/evaluator.py` | ✅ | 5 tests |
| `discover_feeds` | `source_eval/discover.py` | ✅ | Indirecto |
| `derive_selectors` | `source_eval/selectors.py` | ✅ | Indirecto |

### 2.6 Exportación

| Skill | Módulo | Estado | Tests |
|-------|--------|--------|-------|
| `save_documents_jsonl` | `report.py` | ✅ | Indirecto |
| `save_run_report` | `report.py` | ✅ | 5 tests |
| `save_candidates_jsonl` | `search/export.py` | ✅ | Indirecto |
| `export_excel` | Pendiente | 🔲 | — |
| `export_powerbi_json` | Pendiente | 🔲 | — |
| `generate_newsletter_html` | Pendiente | 🔲 | — |

---

## 3. Resumen de Cobertura

| Área | Total | Implementadas | Pendientes |
|------|-------|---------------|------------|
| Core | 8 | 5 | 3 |
| ARAS | 7 | 3 | 4 |
| Riesgos | 8 | 3 | 5 |
| Vigilancia | 11 | 5 | 6 |
| Operaciones | 6 | 6 | 0 |
| Exportación | 6 | 3 | 3 |
| **TOTAL** | **46** | **25 (54%)** | **21 (46%)** |

---

## 4. Contrato de Skill-Code (Ejemplo)

```python
# Cada skill registrada en el registry tiene:
SkillDef(
    name="metadata_match",
    purpose="Match terms against title/snippet/URL metadata without full fetch",
    inputs_schema={
        "title": "str",
        "snippet": "str",
        "terms": "list[str]",
        "url": "str (optional)"
    },
    outputs_schema={
        "score": "float (0.0-1.0)",
        "matched_terms": "list[str]"
    },
    callable=metadata_match,
    version="1.0",
    tags=["matching", "adhoc", "metadata"]
)
```

---

## 5. Prioridad de Implementación de Skills Pendientes

| Prioridad | Skill | Justificación |
|-----------|-------|---------------|
| 1 | `aras_category_classifier` | Valor inmediato para producto Riesgos/ARAS |
| 2 | `risk_type_classifier` | Valor inmediato para producto Riesgos |
| 3 | `export_excel` | Entregable requerido por usuarios |
| 4 | `aras_severity_scoring` + `risk_severity_scoring` | Priorización de alertas |
| 5 | `aras_evidence_spans` + `risk_evidence_spans` | Trazabilidad y auditoría |
| 6 | `relevance_scoring_0_100` | Boletín semanal de vigilancia |
| 7 | `topk_ranker` | Resúmenes ejecutivos |
| 8 | `event_materialization_detector` | Diferenciador para Riesgos |
| 9 | `trend_cluster` | Análisis histórico |
| 10 | `export_powerbi_json` | Consumo por Power BI |
