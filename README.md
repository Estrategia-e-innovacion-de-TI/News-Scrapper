# News Radar MVP

Extractor de noticias multi-fuente con orquestación LangGraph.

## Quickstart

```bash
cd news_radar_mvp
pip install -r requirements.txt
python -m extractor.main --catalog ../catalog.yaml --out out/ --debug
```

## Instalación

```bash
pip install -r requirements.txt

# Playwright (opcional, para sitios JS-heavy)
pip install playwright
playwright install chromium
```

## Modos de Ejecución

### 1. Extracción general (todas las fuentes)

```bash
python -m extractor.main --catalog ../catalog.yaml --out out/ --debug
```

### 2. ARAS ad hoc (empresa + rango de fechas)

Búsqueda ad-hoc por empresa en metadatos (title/summary/snippet/URL) sin fetch masivo.

**Opción 1 (metadata-only)**: Filtra candidatos ANTES de descargar artículos completos.
Esto es rápido y barato porque solo analiza los metadatos del RSS/listing sin hacer
requests HTTP a cada artículo. El scoring es:
- +2 puntos si el término aparece en el título
- +1 punto si aparece en el snippet/summary
- +1 punto si aparece en el slug de la URL
- -30% si el item no tiene `published_at` (menos confiable para el rango de fechas)

```bash
python -m extractor.main --catalog ../catalog.yaml --focus aras_news --adhoc \
  --company "Bancolombia" --date-from 2026-01-01 --date-to 2026-03-01 \
  --topk-per-source 5 --max-candidates-total 50 --out out/aras_adhoc --debug
```

Reglas:
- `--focus aras_news` requiere `--adhoc`, `--company` y rango de fechas
- `--date-from` debe ser <= `--date-to`
- Descubre items vía RSS/listing, filtra por nombre de empresa en title/summary/URL
- Encola solo los TOP-K candidatos por fuente para fetch completo
- El reporte incluye `matched_candidates` (antes de topk) y `selected_candidates` (después)

Provenance en JSONL:
```json
{
  "origin": "adhoc_query",
  "query_type": "aras",
  "query_terms": ["Bancolombia"],
  "query_range": {"from": "2026-01-01", "to": "2026-03-01"}
}
```

### 3. Riesgos ad hoc (NO IMPLEMENTADO AÚN)

> **Nota**: El modo `--focus riesgos_news --adhoc` no está habilitado en esta versión.
> Solo ARAS ad-hoc está disponible. Riesgos se implementará en una fase posterior.

### 4. Vigilancia news semanal

Extracción semanal de noticias por fuentes del catálogo. No soporta adhoc.

```bash
python -m extractor.main --catalog ../catalog.yaml --focus vigilancia_news \
  --days 7 --out out/vigilancia_news_weekly --debug
```

### 5. Vigilancia papers/repos/patentes (Search → Candidates → Ingest)

Flujo en dos pasos: primero buscar candidatos, luego ingestar.

#### Paso 1: Search

```bash
# Papers (ArXiv) - mensual
python -m extractor.search --terms terms_vigilancia.yaml --mode papers \
  --since-days 30 --out out/search/papers

# Repos (GitHub) - mensual
python -m extractor.search --terms terms_vigilancia.yaml --mode repos \
  --since-days 30 --out out/search/repos

# Patentes (Google Patents SERP) - bimensual/trimestral
python -m extractor.search --terms terms_vigilancia.yaml --mode patents \
  --since-days 90 --out out/search/patents
```

Produce:
- `candidates.jsonl` — candidatos filtrados
- `search_report.json` — resumen de búsqueda

#### Paso 2: Ingest candidates

```bash
python -m extractor.main --catalog ../catalog.yaml \
  --candidates out/search/papers/candidates.jsonl \
  --out out/vigilancia_papers --debug
```

### 6. Evaluación de nuevas fuentes (Source Evaluator)

Evalúa nuevas fuentes para inclusión en el catálogo.

```bash
python -m extractor.source_eval --input new_sources.yaml --out out/source_eval
```

Formato de `new_sources.yaml`:

```yaml
sources:
  - source_id: mi_fuente
    name: Mi Fuente
    url: https://example.com
    type: news  # news|repo|patent|paper
```

Para news: detecta RSS, selectores, paywall, valida con 3 artículos.
Para repos/patents/papers: clasifica si corresponde a provider conocido.

Produce:
- `catalog_patch.yaml` — patch para el catálogo
- `source_scorecard.json` — scorecard detallado

## CLI Reference

### extractor.main

```
python -m extractor.main [OPTIONS]

Opciones generales:
  --catalog PATH              Ruta al catalog.yaml (default: catalog.yaml)
  --days N                    Filtrar últimos N días (default: 7)
  --max-items-per-source N    Máximo items por fuente (default: 20)
  --out DIR                   Directorio de salida (default: out)
  --debug                     Modo debug (logs verbose, límite 3 samples/fuente)
  --dry-run                   Descubrir URLs sin descargar
  --only-source ID            Procesar solo esta fuente
  --no-playwright             Deshabilitar Playwright
  --store-raw-html            Guardar HTML raw en debug

Opciones ad-hoc:
  --focus <aras_news|riesgos_news|vigilancia_news>
  --adhoc                     Activar modo ad-hoc
  --company "Nombre"          ARAS: nombre de empresa
  --terms "t1,t2,t3"          Riesgos: términos separados por coma
  --date-from YYYY-MM-DD      Inicio del rango (obligatorio en adhoc)
  --date-to YYYY-MM-DD        Fin del rango (obligatorio en adhoc)
  --topk-per-source K         Top K por fuente (default: 5)
  --max-candidates-total M    Máximo total de candidatos (default: 50)
  --match-mode metadata_only  Modo de matching (fijo en esta fase)

Ingesta de candidatos:
  --candidates PATH           Ruta a candidates.jsonl del search
```

### extractor.search

```
python -m extractor.search [OPTIONS]

  --terms PATH          Ruta a terms YAML (requerido)
  --mode papers|repos|patents  Modo de búsqueda (requerido)
  --out DIR             Directorio de salida (requerido)
  --since-days N        Días hacia atrás (default: 30)
  --max-per-term N      Máximo por término (default: 20)
  --debug               Debug logging
```

### extractor.source_eval

```
python -m extractor.source_eval [OPTIONS]

  --input PATH    Ruta a new_sources.yaml (requerido)
  --out DIR       Directorio de salida (requerido)
  --debug         Debug logging
```

### extractor.ops

```
python -m extractor.ops tier [OPTIONS]

  --catalog PATH        Ruta al catalog.yaml
  --run-report PATH     Ruta al run_report.json
  --out-dir DIR         Directorio de salida
  --prod-mode A|B       Modo de producción (default: B)

python -m extractor.ops diagnose-tier2 [OPTIONS]

  --catalog PATH        Ruta al catalog.yaml
  --run-report PATH     Ruta al run_report.json
  --out-dir DIR         Directorio de salida
```

## Salida

### articles.jsonl

```json
{
  "run_id": "abc123",
  "source_id": "infobae",
  "pipeline_class": "news",
  "focus": ["latam", "general"],
  "title": "Título del artículo",
  "url": "https://...",
  "canonical_url": "https://...",
  "published_at": "2024-03-09T10:00:00",
  "fetched_at": "2024-03-09T15:30:00",
  "language": "es",
  "text": "Contenido extraído...",
  "excerpt": "Primeros 500 caracteres...",
  "raw_len": 45000,
  "text_len": 2500,
  "hash": "sha256...",
  "fetch_method": "rss",
  "status": "ok",
  "source_url": "https://feed.url"
}
```

### search candidates.jsonl

```json
{
  "mode": "papers",
  "term": "fraud detection deep learning",
  "title": "Paper Title",
  "url": "https://arxiv.org/abs/...",
  "snippet": "Abstract excerpt...",
  "published_at": "2026-03-01T...",
  "source_provider": "arxiv",
  "extra": {"authors": "..."}
}
```

## Search Providers

| Modo | Provider | API | Notas |
|------|----------|-----|-------|
| papers | ArXiv | RSS/Atom API | Búsqueda por términos, ordenado por fecha |
| repos | GitHub | REST API v3 | Usa GITHUB_TOKEN si disponible, fallback sin auth |
| patents | Google Patents | Google SERP | Limitado: Google SERP requiere JS, resultados variables |

### Filtros en terms_vigilancia.yaml

```yaml
papers:
  terms: ["fraud detection deep learning", ...]
  filters:
    require_keywords_any: ["fraud", "risk", "cyber"]

repos:
  terms: ["fraud-detection-ml", ...]
  filters:
    min_stars: 10
    updated_within_days: 90

patents:
  terms: ["fraud detection AI", ...]
  filters:
    date_window_months: 6
```

## Operaciones (Tiering & Producción)

### Generar Tiers

```bash
python -m extractor.ops tier \
  --catalog ../catalog.yaml \
  --run-report out/run_report.json \
  --out-dir out/ \
  --prod-mode B
```

### Definición de Tiers

| Tier | Criterio | Descripción |
|------|----------|-------------|
| Tier0 | `text_ok > 0 AND errors == 0` | Prod-ready |
| Tier1 | No es Tier0 ni Tier2 | Condicional: playwright, thin/oversized |
| Tier2 | `errors > 0 OR discovered == 0 OR fetched_ok == 0` | Problemático |

### Modo Producción B

- Incluye Tier0 completo + Tier1 si `text_ok > 0 AND errors == 0`
- Excluye `avg_text_len < 700` (thin_content) y `> 50000` (oversized)
- Separa en `http_lane` y `browser_lane`

### Diagnosticar Tier2

```bash
python -m extractor.ops diagnose-tier2 \
  --catalog ../catalog.yaml \
  --run-report out/run_report.json \
  --out-dir out/
```

## Arquitectura LangGraph

```
load_catalog → select_sources → discover_items → split_lane
                                                     ↓
                    ┌────────────────────────────────┼────────────────────────────────┐
                    ↓                                ↓                                ↓
            fetch_content_http          fetch_content_browser              extract_pdf
                    ↓                                ↓                                ↓
                    └────────────────────────────────┼────────────────────────────────┘
                                                     ↓
                                          persist_and_report → END
```

En modo adhoc, `discover_items` aplica filtrado metadata-only (ARAS/Riesgos) antes de pasar al fetch.
En modo `--candidates`, `discover_items` carga directamente desde JSONL.

## Estructura del Proyecto

```
news_radar_mvp/
├── extractor/
│   ├── main.py              # CLI principal
│   ├── graph.py             # LangGraph pipeline
│   ├── state.py             # Pydantic models
│   ├── catalog.py           # Catalog loader
│   ├── scheduler.py         # Scheduling
│   ├── utils.py             # Utilities
│   ├── report.py            # Metrics & reporting
│   ├── connectors/          # RSS, scrape, browser, PDF
│   ├── extract/             # Text, metadata, normalize, dedupe
│   ├── ops/                 # Tiering & producción
│   │   ├── tiering.py
│   │   ├── catalog_filter.py
│   │   └── __main__.py
│   ├── adhoc/               # ARAS & Riesgos metadata matching
│   │   ├── match.py
│   │   ├── aras.py
│   │   └── riesgos.py
│   ├── search/              # Papers, repos, patents search
│   │   ├── orchestrator.py
│   │   ├── models.py
│   │   ├── loader.py
│   │   ├── filters.py
│   │   ├── export.py
│   │   ├── providers/
│   │   │   ├── arxiv.py
│   │   │   ├── github.py
│   │   │   └── google_patents.py
│   │   └── __main__.py
│   ├── source_eval/         # Source evaluator
│   │   ├── evaluator.py
│   │   ├── discover.py
│   │   ├── selectors.py
│   │   ├── outputs.py
│   │   └── __main__.py
│   ├── capabilities/        # Capabilities (funciones reutilizables)
│   │   ├── registry.py      # Registro de capabilities
│   │   ├── match.py         # Matching por metadata
│   │   ├── ranking.py       # Ranking (placeholder)
│   │   └── classify.py      # Clasificación (placeholder)
│   └── skills/              # DEPRECATED shim → capabilities/
├── playbooks/               # Skills-Docs (instrucciones operativas)
│   ├── ARAS_ADHOC.md
│   ├── RIESGOS_ADHOC.md
│   ├── VIGILANCIA_TECH.md
│   └── SOURCE_ONBOARDING.md
├── docs/
│   ├── VALIDATION_SNAPSHOT.md
│   └── SKILLS_CONCEPT.md
├── tests/
├── terms_vigilancia.yaml
├── pyproject.toml
└── requirements.txt
```

## Capabilities & Playbooks

El proyecto maneja tres capas:

- **Playbooks** (`playbooks/`): Instrucciones operativas en Markdown. Ver `docs/SKILLS_CONCEPT.md`.
- **Capabilities** (`extractor/capabilities/`): Funciones Python reutilizables con contrato definido.
- **Kiro Skills** (`.kiro/skills/`): Instrucciones para el agente AI del IDE.

```python
from extractor.capabilities import get_capability, list_capabilities

# Listar capabilities registradas
for c in list_capabilities():
    print(f"{c.name}: {c.purpose}")

# Usar una capability directamente
cap = get_capability("match_terms")
result = cap.callable("Fraude en Bancolombia", "", ["fraude", "bancolombia"])
print(result)  # {"score": 0.66, "matched_terms": ["fraude", "bancolombia"]}
```

> Nota: `extractor/skills/` sigue existiendo como shim backward-compatible (emite DeprecationWarning).

## Tests

```bash
cd news_radar_mvp
pytest tests/ -v
```

## Troubleshooting

### SSL Errors

El extractor usa `verify=False` para manejar certificados self-signed. Si persisten errores SSL con Playwright:

```bash
NODE_TLS_REJECT_UNAUTHORIZED=0 npx playwright install chromium
```

### Google Patents devuelve 0 resultados

Google Patents es una SPA que requiere JavaScript. El provider usa Google SERP con `site:patents.google.com`, pero Google puede servir CAPTCHAs. Para resultados confiables, considerar SerpAPI o Playwright.

### GitHub rate limit

Sin `GITHUB_TOKEN`, GitHub limita a 10 requests/minuto. Exportar el token:

```bash
export GITHUB_TOKEN=ghp_...
```
