# ARQUITECTURA CONCEPTUAL — News Radar MVP

**Fecha:** 2026-03-16  
**Versión:** 1.0

---

## 1. Vista de Alto Nivel

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERFACES                                │
│  ┌──────────┐  ┌──────────────┐  ┌───────────┐  ┌───────────┐  │
│  │  CLI      │  │  API REST    │  │  Scheduler│  │  Web UI   │  │
│  │ (actual)  │  │  (futuro)    │  │  (básico) │  │  (futuro) │  │
│  └────┬─────┘  └──────┬───────┘  └─────┬─────┘  └─────┬─────┘  │
└───────┼────────────────┼────────────────┼──────────────┼────────┘
        │                │                │              │
┌───────▼────────────────▼────────────────▼──────────────▼────────┐
│                     APPLICATION LAYER                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              LangGraph Pipeline (Orquestador)            │    │
│  │  load_catalog → select_sources → discover_items →        │    │
│  │  split_lane → fetch_http → fetch_browser → extract_pdf → │    │
│  │  persist_and_report                                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Use Case:    │  │ Use Case:    │  │ Use Case:            │  │
│  │ ARAS AdHoc   │  │ Riesgos AdHoc│  │ Vigilancia Semanal   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                      │               │
│  ┌──────▼─────────────────▼──────────────────────▼───────────┐  │
│  │                   Skills Engine                            │  │
│  │  match · classify · rank · score · evidence · cluster      │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬───────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────┐
│                     DOMAIN LAYER                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────┐ │
│  │ Document    │  │ Source     │  │ QueueItem  │  │ RunMetrics│ │
│  │ (Entity)    │  │ Config     │  │ (VO)       │  │ (VO)      │ │
│  └────────────┘  └────────────┘  └────────────┘  └───────────┘ │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │ MatchResult│  │ SearchCand.│  │ SkillDef   │                │
│  │ (VO)       │  │ (VO)       │  │ (VO)       │                │
│  └────────────┘  └────────────┘  └────────────┘                │
│                                                                  │
│  Ports (Interfaces):                                             │
│  SourceRepository · DocumentRepository · SearchProvider ·        │
│  ClassifierService · ScoringService · NotificationService        │
└──────────────────────────────┬───────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────┐
│                   INFRASTRUCTURE LAYER                            │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐   │
│  │ Connectors           │  │ Persistence                     │   │
│  │ ├── RSS (feedparser) │  │ ├── JSONL (local filesystem)    │   │
│  │ ├── Scrape (httpx)   │  │ ├── JSON (run_report)           │   │
│  │ ├── Browser (PW)     │  │ ├── Excel (openpyxl) [futuro]   │   │
│  │ └── PDF (PyPDF2)     │  │ └── S3 (boto3) [futuro]         │   │
│  └─────────────────────┘  └─────────────────────────────────┘   │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐   │
│  │ Search Providers     │  │ LLM Clients                     │   │
│  │ ├── ArXiv (RSS API)  │  │ ├── OpenAI [futuro]             │   │
│  │ ├── GitHub (REST)    │  │ ├── Anthropic [futuro]           │   │
│  │ └── Patents (SERP)   │  │ └── Bedrock [futuro]             │   │
│  └─────────────────────┘  └─────────────────────────────────┘   │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐   │
│  │ Catalog (YAML)       │  │ Notifications                   │   │
│  │ ├── catalog.yaml     │  │ ├── SMTP [futuro]               │   │
│  │ ├── terms_*.yaml     │  │ └── SNS [futuro]                │   │
│  │ └── presets_*.yaml   │  │                                 │   │
│  └─────────────────────┘  └─────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Flujo de Datos

### 2.1 Pipeline Principal (LangGraph)

```
                    catalog.yaml
                        │
                        ▼
              ┌─────────────────┐
              │  load_catalog   │
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │ select_sources  │──── --only-source, --focus
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │ discover_items  │──── RSS/scrape/PDF discovery
              │                 │──── OR candidates.jsonl ingestion
              │                 │──── OR adhoc filtering (ARAS/Riesgos)
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │   split_lane    │──── http / browser / pdf / skipped
              └────────┬────────┘
                       ▼
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
   ┌───────────┐ ┌───────────┐ ┌───────────┐
   │ fetch_http│ │fetch_brows│ │extract_pdf│
   └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
         └─────────────┼─────────────┘
                       ▼
              ┌─────────────────┐
              │persist_and_repo │──── articles.jsonl + run_report.json
              └─────────────────┘
```

### 2.2 Flujo Ad-Hoc (ARAS/Riesgos)

```
  Input: company/terms + date_from + date_to
                    │
                    ▼
         ┌──────────────────┐
         │ discover_items   │  ← Descubre de TODAS las fuentes habilitadas
         └────────┬─────────┘
                  ▼
         ┌──────────────────┐
         │ adhoc_filter     │  ← metadata_match + date_range + topK
         │ (aras/riesgos)   │
         └────────┬─────────┘
                  ▼
         ┌──────────────────┐
         │ fetch + extract  │  ← Solo candidatos seleccionados
         └────────┬─────────┘
                  ▼
         ┌──────────────────┐
         │ [FUTURO] LLM     │  ← Clasificación + severidad + evidencia
         │ classify + score │
         └────────┬─────────┘
                  ▼
         ┌──────────────────┐
         │ persist          │  ← JSONL + run_report + [FUTURO] Excel
         └──────────────────┘
```

### 2.3 Flujo Search Agent (Vigilancia)

```
  terms_vigilancia.yaml
          │
          ▼
  ┌───────────────┐
  │ load_terms    │
  └───────┬───────┘
          ▼
  ┌───────────────┐     ┌──────────┐
  │ search_arxiv  │────▶│          │
  ├───────────────┤     │ apply    │     ┌──────────────┐
  │ search_github │────▶│ filters  │────▶│ candidates   │
  ├───────────────┤     │          │     │ .jsonl       │
  │ search_patents│────▶│          │     └──────┬───────┘
  └───────────────┘     └──────────┘            │
                                                ▼
                                    ┌──────────────────┐
                                    │ Pipeline principal│
                                    │ --candidates      │
                                    └──────────────────┘
```

---

## 3. Componentes por Producto

### 3.1 Producto Riesgos

```
┌─────────────────────────────────────────────┐
│              Producto Riesgos                │
│                                             │
│  ┌──────────────┐  ┌────────────────────┐   │
│  │  ARAS AdHoc  │  │ Riesgos Emergentes │   │
│  │              │  │                    │   │
│  │ Input:       │  │ Input:             │   │
│  │  company/NIT │  │  terms (libre)     │   │
│  │  date range  │  │  date range        │   │
│  │              │  │                    │   │
│  │ Skills:      │  │ Skills:            │   │
│  │  match       │  │  match             │   │
│  │  classify*   │  │  classify*         │   │
│  │  severity*   │  │  risk_type*        │   │
│  │  evidence*   │  │  event_detect*     │   │
│  │              │  │  severity*         │   │
│  │ Output:      │  │  evidence*         │   │
│  │  JSONL       │  │                    │   │
│  │  Excel*      │  │ Output:            │   │
│  │  run_report  │  │  JSONL             │   │
│  └──────────────┘  │  Excel*            │   │
│                    │  run_report        │   │
│  * = pendiente     └────────────────────┘   │
└─────────────────────────────────────────────┘
```

### 3.2 Producto Vigilancia Tecnológica

```
┌──────────────────────────────────────────────────────┐
│           Producto Vigilancia Tecnológica              │
│                                                        │
│  ┌─────────────────────┐  ┌────────────────────────┐  │
│  │  Boletín Semanal    │  │  Análisis Histórico    │  │
│  │  (News)             │  │  (Papers/Repos/Patents)│  │
│  │                     │  │                        │  │
│  │ Frecuencia: semanal │  │ Papers: mensual        │  │
│  │ Fuentes: catálogo   │  │ Repos: mensual         │  │
│  │                     │  │ Patents: trimestral    │  │
│  │ Skills:             │  │                        │  │
│  │  score_0_100*       │  │ Skills:                │  │
│  │  topk_ranker*       │  │  cluster*              │  │
│  │  newsletter*        │  │  trend_map*            │  │
│  │                     │  │  novelty*              │  │
│  │ Output:             │  │  hype_cycle*           │  │
│  │  Top-10 MD/HTML*    │  │                        │  │
│  │  Email*             │  │ Output:                │  │
│  └─────────────────────┘  │  JSON (Power BI)*      │  │
│                           │  Annual report*        │  │
│  * = pendiente            └────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

---

## 4. Modelo de Datos

### 4.1 Entidades Principales

```
Document
├── run_id: str (UUID corto)
├── source_id: str
├── pipeline_class: news|evidence|reports|papers
├── focus: list[str]
├── title: str
├── url: str
├── canonical_url: str?
├── published_at: str? (ISO8601)
├── fetched_at: str
├── language: es|en|pt|unknown
├── text: str
├── excerpt: str (500 chars)
├── raw_len: int
├── text_len: int
├── text_capped: bool
├── hash: str (SHA256)
├── fetch_method: rss|http|playwright|pdf
├── status: ok|error
├── source_url: str
├── origin: catalog|adhoc_query|search_ingest
├── query_type: aras|riesgos|null
├── query_terms: list[str]
└── query_range: {from, to}

SourceConfig
├── source_id: str
├── name: str
├── enabled: bool
├── availability: open|gated|blocked|unknown
├── focus: list[str]
├── pipeline_class: str
├── type: rss|scrape|pdf|query|custom
├── base_url: str
├── rss_urls: list[str]
├── listing_urls: list[str]
├── pdf_urls: list[str]
├── languages: list[str]
├── geo: list[str]
├── topics: list[str]
├── requires_playwright: bool
├── selectors: dict
├── quality_hint: stable|ok|fragile
└── timeout_seconds, max_retries, rate_limit_rps, min_text_chars

GraphState (LangGraph)
├── run_id, started_at
├── CLI params (catalog_path, days, out_dir, focus, adhoc, company, terms, ...)
├── Catalog data (defaults, sources, selected_sources)
├── Processing queues (queue, http_queue, browser_queue, pdf_queue, skipped_queue)
├── Results (documents, seen_hashes)
├── Metrics (metrics, source_metrics)
└── Errors (errors)
```

### 4.2 Catálogo de Fuentes (37 fuentes)

| Categoría | Fuentes | Tipo | Focus |
|-----------|---------|------|-------|
| Colombia/LATAM Prensa | 8 | RSS/scrape | aras_latam, riesgos_latam |
| ARAS Evidencia Colombia | 6 | scrape/query/custom | aras_latam |
| Ciberseguridad | 6 | RSS/scrape | vigilancia_global, riesgos_latam |
| Reportes Riesgos | 4 | PDF/scrape | riesgos_latam, vigilancia_global |
| Vigilancia Tech/Banca | 13 | RSS/scrape | vigilancia_global |
| **Total** | **37** | | |

---

## 5. Tecnologías

| Componente | Tecnología | Versión |
|------------|-----------|---------|
| Orquestación | LangGraph | ≥0.2.0 |
| HTTP Client | httpx | ≥0.27.0 |
| RSS Parser | feedparser | ≥6.0.0 |
| HTML Parser | BeautifulSoup4, lxml | ≥4.12.0, ≥5.0.0 |
| Text Extraction | trafilatura, readability-lxml | ≥1.12.0, ≥0.8.0 |
| PDF | PyPDF2 | ≥3.0.0 |
| Browser | Playwright | ≥1.40.0 (opcional) |
| Models | Pydantic | ≥2.0.0 |
| Config | PyYAML | ≥6.0.0 |
| Tests | pytest, pytest-asyncio | ≥8.0.0 |
| Python | CPython | ≥3.11 |

### Dependencias Futuras (no instaladas aún)

| Componente | Tecnología | Para |
|------------|-----------|------|
| Excel | openpyxl o xlsxwriter | REQ-12 |
| LLM | langchain-openai / langchain-anthropic / boto3 (Bedrock) | REQ-1, REQ-2 |
| Clustering | scikit-learn | REQ-5 |
| Email | smtplib (stdlib) + jinja2 | REQ-4 |
| AWS | boto3, aws-cdk-lib | REQ-11 |
| NIT Resolution | httpx (RUES API) | REQ-1 |
