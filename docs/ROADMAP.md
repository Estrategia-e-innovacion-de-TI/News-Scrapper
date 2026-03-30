# ROADMAP — News Radar MVP

**Fecha:** 2026-03-16  
**Programa:** News Radar — Plataforma de Inteligencia de Noticias y Vigilancia Tecnológica  
**Estado actual:** MVP funcional con extracción, adhoc, search, source_eval, tiering, 93 tests.

---

## Métricas de Éxito

| Área | Métrica | Objetivo |
|------|---------|----------|
| Extracción | text_ok_rate | ≥ 80% sobre Tier0+Tier1 |
| Extracción | 403_rate | < 5% sobre fuentes habilitadas |
| Calidad | avg_text_len | 800–15000 chars para noticias |
| Calidad | duplicate_rate | < 10% por run |
| Utilidad | Top-10 score | > 50 para items seleccionados |
| Utilidad | Diversidad Top-10 | ≥ 5 fuentes distintas |
| Rendimiento | Tiempo adhoc | < 5 min para 50 candidatos |
| Cobertura | Idiomas | ≥ 2 (es, en) |
| Cobertura | Geos | ≥ 3 (LATAM, US/EU, Global) |

---

## Sprint 0 — Hardening y Observabilidad (2 semanas)

**Objetivo:** Estabilizar MVP, mejorar observabilidad.

| Tarea | Prioridad | Esfuerzo |
|-------|-----------|----------|
| Migrar `class Config` a `model_config = ConfigDict(...)` | Alta | 1h |
| Tipificar errores "unknown" (heurísticas timeout/DNS/SSL) | Media | 4h |
| Implementar `boilerplate_trim` (cap 20K + detección repetición) | Media | 4h |
| Agregar timing por nodo en run_report.json | Baja | 2h |
| Agregar logging estructurado JSON (`--log-format json`) | Baja | 2h |
| Health check de fuentes (`python -m extractor.ops health`) | Baja | 4h |

**Criterios de aceptación:** 0 warnings Pydantic, errores "unknown" < 5%, 93+ tests.

---

## Sprint 1 — Clasificación LLM + Excel (3 semanas)

**Objetivo:** Implementar clasificación LLM y generación de Excel para ARAS y Riesgos.

| Tarea | Prioridad | Esfuerzo |
|-------|-----------|----------|
| Implementar `ClassifierService` (Protocol + rules + LLM) | Alta | 8h |
| Implementar `aras_category_classifier` (rules v1 + LLM v2) | Alta | 6h |
| Implementar `risk_type_classifier` (rules v1 + LLM v2) | Alta | 6h |
| Implementar `severity_scoring` H/M/L con confianza | Alta | 4h |
| Implementar `evidence_spans` (±150 chars alrededor de matches) | Alta | 4h |
| Implementar `export_excel` (openpyxl) con columnas estándar | Alta | 4h |
| Implementar `event_materialization_detector` (regex patterns) | Media | 4h |
| Agregar `--classifier rules\|llm` flag al CLI | Media | 1h |
| Tests: classify, severity, evidence, excel | Alta | 6h |

**Dependencias:** Sprint 0 (boilerplate_trim).  
**Criterios de aceptación:** Clasificador asigna categoría a ≥ 70% docs, Excel generado con todas las columnas.

---

## Sprint 2 — Scoring Vigilancia + Suscripciones (3 semanas)

**Objetivo:** Implementar scoring 0..100, Top-10, suscripciones por tema.

| Tarea | Prioridad | Esfuerzo |
|-------|-----------|----------|
| Implementar `relevance_scoring_0_100` con rúbrica configurable | Alta | 6h |
| Implementar `topk_ranker` con diversidad de fuentes | Alta | 4h |
| Implementar query_groups en terms_vigilancia.yaml (ES+EN) | Alta | 4h |
| Implementar filtrado por query_groups del suscriptor | Alta | 4h |
| Implementar `subscribers.yaml` con temas por usuario | Media | 2h |
| Generar `top10_summary.md` y `top10_summary.html` | Media | 4h |
| Implementar presets de términos riesgos | Baja | 2h |
| Tests: scoring, topk, query_groups, subscribers | Alta | 6h |

**Dependencias:** Sprint 1 (clasificación).  
**Criterios de aceptación:** Score 0..100 asignado, Top-10 con ≥ 5 fuentes, filtrado por suscriptor funcional.

---

## Sprint 3 — Análisis Histórico + Power BI (3 semanas)

**Objetivo:** Clustering, trends, JSON para Power BI.

| Tarea | Prioridad | Esfuerzo |
|-------|-----------|----------|
| Implementar `trend_cluster` (TF-IDF + cosine similarity) | Alta | 8h |
| Implementar `novelty_score` (Jaccard vs corpus histórico) | Media | 4h |
| Implementar `hype_cycle_indicator` (momentum + maturity) | Media | 6h |
| Implementar `export_powerbi_json` con schema definido | Alta | 4h |
| Mejorar Google Patents provider (SerpAPI o Playwright) | Media | 6h |
| Implementar deduplicación cross-run en candidates | Baja | 4h |
| Agregar `--since-days` efectivo en ArXiv y GitHub | Baja | 2h |
| Tests: cluster, novelty, powerbi_json | Alta | 6h |

**Dependencias:** Sprint 2 (scoring), scikit-learn como nueva dependencia.  
**Criterios de aceptación:** Clusters con ≥ 3 items, JSON Power BI generado, ≥ 2 providers retornan resultados.

---

## Sprint 4 — Newsletter + Email (2 semanas)

**Objetivo:** Generación y distribución de newsletters.

| Tarea | Prioridad | Esfuerzo |
|-------|-----------|----------|
| Implementar generador newsletter HTML (Jinja2) | Alta | 6h |
| Implementar envío SMTP con configuración YAML | Media | 4h |
| Implementar `--newsletter` flag (generar sin enviar) | Media | 1h |
| Implementar `--send-email` flag | Media | 1h |
| Tests: newsletter_generator | Media | 3h |

**Dependencias:** Sprint 2 (Top-10, suscripciones).  
**Criterios de aceptación:** Newsletter HTML generado, email enviado a suscriptores.

---

## Sprint 5 — Resolución NIT + Mejoras ARAS (2 semanas)

**Objetivo:** Completar funcionalidades ARAS pendientes.

| Tarea | Prioridad | Esfuerzo |
|-------|-----------|----------|
| Implementar `aras_nit_resolver` (RUES API o similar) | Media | 6h |
| Agregar `--nit` flag al CLI como alternativa a `--company` | Media | 1h |
| Implementar `matched_candidates.jsonl` como output adicional | Baja | 2h |
| Mejorar adhoc_summary con candidates_evaluated/matched/fetched | Baja | 2h |
| Tests: nit_resolver, matched_candidates | Media | 3h |

**Dependencias:** Sprint 1 (clasificación ARAS).  
**Criterios de aceptación:** NIT resuelto a nombre, matched_candidates generado.

---

## Sprint 6 — Clean Architecture Migration (4 semanas)

**Objetivo:** Migrar a estructura domain/application/infrastructure/interfaces.

| Tarea | Prioridad | Esfuerzo |
|-------|-----------|----------|
| Fase 1: Extraer domain/ (entities, VOs, ports, services) | Alta | 12h |
| Fase 2: Extraer infrastructure/ (connectors, persistence, providers) | Alta | 12h |
| Fase 3: Crear application/ (use cases, DI container) | Alta | 12h |
| Fase 4: Refactorizar interfaces/ (CLI limpio) | Media | 6h |
| Mantener backward compatibility (re-exports) | Alta | 4h |
| Migrar tests a nueva estructura | Alta | 6h |

**Dependencias:** Sprints 1-5 completados (evitar migrar código en flux).  
**Criterios de aceptación:** Todos los tests pasan, CLI funciona igual, imports limpios entre capas.

---

## Sprint 7 — AWS SBX Deployment (2 semanas)

**Objetivo:** Desplegar en AWS SBX.

| Tarea | Prioridad | Esfuerzo |
|-------|-----------|----------|
| Crear Dockerfile optimizado | Alta | 2h |
| Crear CDK stacks (pipeline, storage, monitoring) | Alta | 8h |
| Configurar ECR + ECS Fargate | Alta | 4h |
| Configurar S3 bucket con estructura de prefijos | Media | 2h |
| Configurar Secrets Manager | Media | 1h |
| Configurar EventBridge schedules | Media | 2h |
| Configurar SNS notifications | Baja | 1h |
| Validar con run manual en AWS | Alta | 2h |
| Configurar CI/CD (GitHub Actions) | Media | 4h |

**Dependencias:** Sprint 6 (Clean Architecture facilita containerización).  
**Criterios de aceptación:** Run exitoso en Fargate, artifacts en S3, costo < $50/mes.

---

## Diagrama de Dependencias

```
S0 (Hardening) ─────────────────────────────────────────┐
 │                                                       │
 ├── S1 (Clasificación LLM + Excel) ────────┐           │
 │                                           │           │
 │   S2 (Scoring + Suscripciones) ──────────┤           │
 │    │                                      │           │
 │    ├── S3 (Análisis Histórico + PBI) ────┤           │
 │    │                                      │           │
 │    └── S4 (Newsletter + Email) ──────────┘           │
 │                                                       │
 ├── S5 (NIT + Mejoras ARAS) ── paralelo con S2-S4     │
 │                                                       │
 └── S6 (Clean Architecture) ── después de S1-S5 ──────┤
                                                         │
     S7 (AWS SBX) ── después de S6 ─────────────────────┘
```

---

## Timeline Estimado

| Sprint | Duración | Semana inicio | Semana fin |
|--------|----------|---------------|------------|
| S0 | 2 semanas | W1 | W2 |
| S1 | 3 semanas | W3 | W5 |
| S2 | 3 semanas | W6 | W8 |
| S3 | 3 semanas | W9 | W11 |
| S4 | 2 semanas | W12 | W13 |
| S5 | 2 semanas | W6 | W7 (paralelo) |
| S6 | 4 semanas | W14 | W17 |
| S7 | 2 semanas | W18 | W19 |
| **TOTAL** | **~19 semanas** | | |
