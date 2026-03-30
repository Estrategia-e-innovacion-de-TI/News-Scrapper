# SPEC — News Radar MVP

**Versión:** 1.0  
**Fecha:** 2026-03-16  
**Estado:** Borrador definitivo

---

## 1. Visión General

News Radar es una plataforma de inteligencia de noticias y vigilancia tecnológica para equipos de ARAS, Riesgos Emergentes y Vigilancia Tecnológica. Extrae, filtra, clasifica y distribuye información relevante desde fuentes abiertas.

### 1.1 Productos

| Producto | Subflujos | Tipo de consulta | Fuentes |
|----------|-----------|------------------|---------|
| **Riesgos (Front)** | ARAS, Riesgos Emergentes | Ad-hoc (solo noticias) | Catálogo news (37 fuentes) |
| **Vigilancia Tecnológica (Front)** | Boletín semanal, Análisis histórico | Suscripción + periódico | News, papers, repos, patentes |

### 1.2 Inventario del Repo Actual

```
news_radar_mvp/
├── extractor/
│   ├── main.py          # CLI entry point (argparse)
│   ├── graph.py          # LangGraph pipeline (8 nodos)
│   ├── state.py          # Pydantic state models
│   ├── catalog.py        # Catalog YAML loader
│   ├── report.py         # Run report + JSONL persistence
│   ├── scheduler.py      # Simple periodic scheduler
│   ├── utils.py          # Rate limiter, retry, normalize, detect_language
│   ├── adhoc/            # ARAS + Riesgos ad-hoc matching
│   │   ├── aras.py       # company_to_terms, filter_aras_candidates
│   │   ├── riesgos.py    # parse_terms, filter_riesgos_candidates
│   │   └── match.py      # metadata_match, rank_candidates (Opción 1)
│   ├── connectors/       # RSS, scrape, browser (Playwright), PDF
│   ├── extract/          # text (trafilatura/readability/bs4), metadata, dedupe, normalize
│   ├── ops/              # tiering, catalog_filter, CLI ops
│   ├── search/           # Search agent: ArXiv, GitHub, Google Patents
│   │   ├── orchestrator.py
│   │   ├── providers/    # arxiv.py, github.py, google_patents.py
│   │   ├── models.py     # SearchCandidate, SearchReport
│   │   ├── filters.py    # Mode-specific filters
│   │   ├── loader.py     # YAML terms loader
│   │   └── export.py     # JSONL + report export
│   ├── skills/           # Registry + match + classify (placeholder) + ranking (placeholder)
│   └── source_eval/      # Source evaluator: discover, evaluate, selectors, outputs
├── playbooks/            # Skills-Docs (ARAS, Riesgos, Vigilancia, Source Onboarding)
├── tests/                # 93 tests (pytest)
├── out/                  # Output artifacts
├── catalog.yaml          # 37 fuentes definidas
├── catalog_patch.yaml    # Patches de source_eval
├── source_profiles.json  # Perfiles de fuentes evaluadas
└── terms_vigilancia.yaml # Términos de búsqueda para vigilancia
```

---

## 2. Producto Riesgos (Front)

### 2.1 ARAS Ad-Hoc

**Entrada:**
- Nombre de empresa (texto libre) O NIT
- Rango de fechas: date_from (YYYY-MM-DD), date_to (YYYY-MM-DD)
- Parámetros opcionales: topk_per_source (default: 5), max_candidates_total (default: 50)

**Flujo:**
1. Descubrir items de fuentes con focus `aras_latam` (RSS/scrape)
2. Filtrar por rango de fechas (published_at vs date_from/date_to)
3. Matching metadata-only: título (2pts) + snippet (1pt) + URL slug (1pt)
4. Top-K por fuente → Top-K global
5. Fetch completo de candidatos seleccionados
6. Extracción de texto + deduplicación
7. **[GAP]** Clasificación LLM por categoría ARAS
8. **[GAP]** Scoring de severidad H/M/L con evidencia
9. **[GAP]** Generación de Excel

**Salida esperada (Excel):**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| título | string | Título del artículo |
| medio | string | source_id de la fuente |
| fecha | date | published_at (ISO8601) |
| URL | string | URL canónica del artículo |
| resumen_corto | string | Excerpt de 500 chars |
| categoría | string | Clasificación LLM (lavado_activos, fraude, corrupcion, sanciones, pep, ambiental, social, otro) |
| severidad | H/M/L | Nivel de severidad asignado |
| evidencia_citas | string | Fragmentos textuales que respaldan la clasificación |

**Estado actual:** Matching metadata-only implementado. Faltan: resolución NIT, clasificación LLM, severidad, evidencia, Excel.

### 2.2 Riesgos Emergentes Ad-Hoc

**Entrada:**
- Términos de riesgo (texto libre, comma-separated) O preset (ciber|fraude|operacional|all)
- Rango de fechas: date_from, date_to

**Flujo:** Análogo a ARAS, con clasificación por tipo de riesgo en lugar de categoría ARAS.

**Categorías de riesgo:**
- cibernetico, operacional, fraude, asg, ia, talento, regulatorio, otro

**Eventos materializados a detectar:**
- multa, perdida, outage, breach, near_miss, sancion, demanda

**Estado actual:** Matching metadata-only implementado. Faltan: clasificación LLM, detección de eventos, severidad, evidencia, Excel, presets.

---

## 3. Producto Vigilancia Tecnológica (Front)

### 3.1 Suscripción a Boletín

**Modelo de suscripción:**
- Cada usuario/suscriptor se asocia a uno o más temas (query_groups)
- Solo recibe contenido relevante a sus temas de interés
- No se procesa contenido global; el análisis se limita a los términos configurados

**query_groups propuestos (ES + EN):**

| Grupo | Términos ES | Términos EN |
|-------|-------------|-------------|
| ia_ml | inteligencia artificial, aprendizaje automático, LLM, GPT, redes neuronales | artificial intelligence, machine learning, deep learning, LLM, neural networks |
| blockchain | blockchain, criptomonedas, DeFi, contratos inteligentes, tokenización | blockchain, cryptocurrency, DeFi, smart contracts, tokenization |
| ciberseguridad | ciberseguridad, ransomware, phishing, vulnerabilidad, amenaza | cybersecurity, ransomware, phishing, vulnerability, threat intelligence |
| fintech | fintech, banca digital, pagos digitales, neobancos, open banking | fintech, digital banking, digital payments, neobanks, open banking |
| regtech | regulación tecnológica, cumplimiento, AML, KYC, PLD | regtech, compliance, AML, KYC, anti-money laundering |
| cloud | nube, cloud computing, serverless, contenedores, microservicios | cloud computing, serverless, containers, microservices, kubernetes |
| datos | big data, analítica, data lake, gobernanza de datos, calidad de datos | big data, analytics, data lake, data governance, data quality |
| banca_digital | transformación digital banca, core bancario, modernización legacy | digital transformation banking, core banking, legacy modernization |

### 3.2 Flujo Analítico Semanal (Noticias)

**Frecuencia:** Semanal  
**Fuentes:** Catálogo con focus `vigilancia_global`  
**Proceso:**
1. Extraer noticias de últimos 7 días
2. Filtrar por relevancia respecto a query_groups del suscriptor
3. Asignar score 0..100 por noticia

**Rúbrica de Scoring 0..100:**

| Factor | Peso | Cálculo |
|--------|------|---------|
| keyword_density | 40% | (términos_matched / total_términos) × 100 |
| recency | 20% | max(0, 100 - (días_antigüedad × 14.3)) |
| source_authority | 20% | Score fijo por fuente (tier0=100, tier1=70, tier2=30) |
| topic_alignment | 20% | Coincidencia con query_group del suscriptor (0 o 100) |

**Score final:** Σ(factor × peso), redondeado a entero.

**Salida:** Top-10 items con score > 50, diversidad ≥ 5 fuentes.

### 3.3 Flujo Analítico Histórico

**Frecuencias:**
- Papers (ArXiv): mensual
- Repos (GitHub): mensual
- Patentes: trimestral

**Proceso:**
1. Search por términos de terms_vigilancia.yaml
2. Filtrado por modo (min_stars, require_keywords, date_window)
3. Ingesta de candidatos en pipeline principal
4. Clustering (TF-IDF + cosine similarity)
5. Trend mapping temporal
6. Novelty scoring vs corpus histórico

**Salida JSON para Power BI:**

```json
{
  "meta": {
    "generated_at": "2026-03-16T00:00:00Z",
    "period": "2025-Q4",
    "modes": ["papers", "repos", "patents"]
  },
  "clusters": [
    {
      "cluster_id": "c1",
      "label": "LLM Security",
      "centroid_keywords": ["llm", "security", "vulnerability", "prompt injection"],
      "item_count": 12,
      "items": [
        {"title": "...", "url": "...", "mode": "papers", "score": 85, "published_at": "..."}
      ]
    }
  ],
  "trend_timeline": [
    {"date": "2025-10", "topic": "ia_ml", "count": 45, "avg_score": 72},
    {"date": "2025-11", "topic": "ia_ml", "count": 52, "avg_score": 78}
  ],
  "hype_indicators": [
    {"topic": "ia_ml", "momentum": 0.85, "maturity_stage": "peak_of_inflated_expectations"},
    {"topic": "blockchain", "momentum": 0.45, "maturity_stage": "slope_of_enlightenment"}
  ],
  "top_items": [
    {"title": "...", "url": "...", "mode": "papers", "score": 95, "cluster_id": "c1"}
  ]
}
```

---

## 4. JSON Schemas

### 4.1 Document (salida principal)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["run_id", "source_id", "title", "url", "fetched_at", "text", "hash", "fetch_method", "source_url"],
  "properties": {
    "run_id": {"type": "string"},
    "source_id": {"type": "string"},
    "pipeline_class": {"type": "string", "enum": ["news", "evidence", "reports", "papers"]},
    "focus": {"type": "array", "items": {"type": "string"}},
    "title": {"type": "string"},
    "url": {"type": "string", "format": "uri"},
    "canonical_url": {"type": ["string", "null"]},
    "published_at": {"type": ["string", "null"]},
    "fetched_at": {"type": "string"},
    "language": {"type": "string"},
    "text": {"type": "string"},
    "excerpt": {"type": "string"},
    "raw_len": {"type": "integer"},
    "text_len": {"type": "integer"},
    "text_capped": {"type": "boolean"},
    "hash": {"type": "string"},
    "fetch_method": {"type": "string"},
    "status": {"type": "string"},
    "source_url": {"type": "string"},
    "origin": {"type": "string", "enum": ["catalog", "adhoc_query", "search_ingest"]},
    "query_type": {"type": ["string", "null"], "enum": ["aras", "riesgos", null]},
    "query_terms": {"type": "array", "items": {"type": "string"}},
    "query_range": {"type": "object", "properties": {"from": {"type": "string"}, "to": {"type": "string"}}}
  }
}
```

### 4.2 Adhoc Query Input

```json
{
  "type": "object",
  "required": ["focus", "date_from", "date_to"],
  "properties": {
    "focus": {"type": "string", "enum": ["aras_news", "riesgos_news"]},
    "company": {"type": "string", "description": "Solo para ARAS"},
    "nit": {"type": "string", "description": "Solo para ARAS, alternativa a company"},
    "terms": {"type": "string", "description": "Solo para Riesgos, comma-separated"},
    "terms_preset": {"type": "string", "enum": ["ciber", "fraude", "operacional", "all"]},
    "date_from": {"type": "string", "format": "date"},
    "date_to": {"type": "string", "format": "date"},
    "topk_per_source": {"type": "integer", "default": 5},
    "max_candidates_total": {"type": "integer", "default": 50}
  }
}
```

### 4.3 Run Report

```json
{
  "type": "object",
  "required": ["run_id", "started_at", "summary"],
  "properties": {
    "run_id": {"type": "string"},
    "started_at": {"type": "string"},
    "finished_at": {"type": "string"},
    "duration_seconds": {"type": "number"},
    "summary": {
      "type": "object",
      "properties": {
        "total_sources": {"type": "integer"},
        "total_discovered": {"type": "integer"},
        "total_fetched": {"type": "integer"},
        "total_ok": {"type": "integer"},
        "total_skipped": {"type": "integer"},
        "total_errors": {"type": "integer"},
        "total_dupes": {"type": "integer"}
      }
    },
    "by_source": {"type": "object"},
    "params": {"type": "object"},
    "adhoc_summary": {
      "type": "object",
      "properties": {
        "focus": {"type": "string"},
        "query_type": {"type": "string"},
        "company": {"type": ["string", "null"]},
        "terms": {"type": ["string", "null"]},
        "date_from": {"type": "string"},
        "date_to": {"type": "string"},
        "candidates_evaluated": {"type": "integer"},
        "candidates_matched": {"type": "integer"},
        "candidates_fetched": {"type": "integer"}
      }
    }
  }
}
```

---

## 5. Trazabilidad

Cada ejecución genera:
- `run_id` (UUID corto de 8 chars)
- `run_report.json` con parámetros, métricas, errores
- `articles.jsonl` con provenance por documento
- Campos de provenance: origin, query_type, query_terms, query_range
- Error tracking: source_id, phase, error_type (enum tipificado), error_msg

---

## 6. Reglas de Volumen y Rendimiento

| Parámetro | Default | Configurable | Descripción |
|-----------|---------|-------------|-------------|
| topk_per_source | 5 | --topk-per-source | Candidatos por fuente (adhoc) |
| max_candidates_total | 50 | --max-candidates-total | Candidatos globales (adhoc) |
| max_items_per_source | 20 | --max-items-per-source | Items por fuente (catálogo) |
| max_text_chars | 50000 | --max-text-chars | Cap de texto por documento |
| rate_limit_rps | 1.0 | catalog.yaml defaults | Requests/segundo por fuente |
| timeout_seconds | 25 | catalog.yaml defaults | Timeout HTTP por request |
| max_retries | 2 | catalog.yaml defaults | Reintentos por request |
| days | 7 | --days | Ventana temporal (catálogo) |

---

## 7. Políticas de Matching

### 7.1 Normalización
- Lowercase
- Strip acentos (NFKD + remove combining chars)
- Colapsar whitespace múltiple a espacio simple

### 7.2 Scoring
- Match en título: 2 puntos por término
- Match en snippet: 1 punto por término
- Match en URL slug: 1 punto por término
- Score normalizado: raw_score / (num_terms × 4)
- Rango: 0.0 - 1.0

### 7.3 Filtros
- Solo candidatos con score > 0
- Items sin published_at: incluidos con penalización ×0.7 (solo ARAS con rango de fechas)
- Deduplicación: SHA256 sobre título_normalizado + primeros 2000 chars de texto_normalizado

---

## 8. Resumen Ejecutivo

### Estado Actual
- Pipeline LangGraph funcional con 8 nodos
- 37 fuentes en catálogo (8 RSS, 15 requieren Playwright, 5 paywall, 2 custom pendientes)
- ARAS y Riesgos ad-hoc con metadata-only matching
- Search agent para papers (ArXiv), repos (GitHub), patentes (Google Patents, limitado)
- Source evaluator con detección de RSS, paywall, Playwright
- Tiering operativo (Tier0/1/2) con modo producción B
- 93 tests pasando

### Gaps Principales
1. **Clasificación LLM** — No implementada (classify.py es placeholder)
2. **Severidad H/M/L** — No implementada
3. **Evidencia (citas textuales)** — No implementada
4. **Excel output** — No implementado
5. **Resolución NIT** — No implementada
6. **Scoring 0..100 para vigilancia** — No implementado
7. **Clustering/trends/hype cycles** — No implementado
8. **JSON para Power BI** — No implementado
9. **Suscripciones por usuario/tema** — No implementadas
10. **Newsletter HTML/email** — No implementado

### Top 10 Tareas Siguientes
1. Implementar clasificador LLM para ARAS (categorías) y Riesgos (tipos)
2. Implementar scoring de severidad H/M/L con evidencia (citas)
3. Implementar generación de Excel para consultas ad-hoc
4. Implementar scoring 0..100 con rúbrica configurable para vigilancia
5. Implementar clustering TF-IDF para análisis histórico
6. Implementar JSON output para Power BI
7. Implementar resolución NIT → nombre de empresa
8. Implementar suscripciones por usuario/tema
9. Migrar a Clean Architecture (domain/application/infrastructure/interfaces)
10. Crear plan de despliegue AWS SBX con IaC (CDK/SAM)
