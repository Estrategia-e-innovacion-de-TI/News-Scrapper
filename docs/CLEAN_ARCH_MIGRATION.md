# PLAN DE MIGRACIÓN A CLEAN ARCHITECTURE — News Radar MVP

**Fecha:** 2026-03-16  
**Versión:** 1.0

---

## 1. Estado Actual

El código vive en una estructura plana bajo `extractor/`:

```
extractor/
├── main.py           # CLI + entry point
├── graph.py          # LangGraph pipeline + nodos + lógica de negocio mezclada
├── state.py          # Modelos Pydantic (domain + state)
├── catalog.py        # Loader YAML (infra)
├── report.py         # Persistencia JSONL/JSON (infra)
├── scheduler.py      # Scheduling (infra)
├── utils.py          # Utilidades mixtas (domain + infra)
├── adhoc/            # Lógica de negocio adhoc
├── connectors/       # Infraestructura de fetch
├── extract/          # Lógica de extracción (domain + infra)
├── ops/              # Operaciones (application)
├── search/           # Search agent (application + infra)
├── skills/           # Skills engine (domain)
└── source_eval/      # Source evaluator (application + infra)
```

**Problemas:**
- `graph.py` mezcla orquestación, lógica de negocio y acceso a infraestructura
- `state.py` mezcla entidades de dominio con estado de pipeline
- `utils.py` mezcla utilidades de dominio (normalize) con infraestructura (rate_limiter)
- Imports directos entre capas (connectors importados directamente en graph.py)
- No hay interfaces/protocolos definidos

---

## 2. Estructura Objetivo

```
news_radar/
├── domain/                          # Capa de dominio (sin dependencias externas)
│   ├── entities/
│   │   ├── document.py              # Document entity
│   │   ├── source.py                # SourceConfig entity
│   │   └── search_candidate.py      # SearchCandidate entity
│   ├── value_objects/
│   │   ├── queue_item.py            # QueueItem VO
│   │   ├── match_result.py          # MatchResult VO
│   │   ├── run_metrics.py           # RunMetrics, SourceMetrics VO
│   │   └── enums.py                 # FetchMethod, ItemStatus, ErrorType, SkipReason
│   ├── ports/                       # Interfaces (Protocol classes)
│   │   ├── source_repository.py     # Protocol: load, filter sources
│   │   ├── document_repository.py   # Protocol: save documents, reports
│   │   ├── content_fetcher.py       # Protocol: fetch HTML/PDF
│   │   ├── text_extractor.py        # Protocol: extract text from HTML
│   │   ├── search_provider.py       # Protocol: search papers/repos/patents
│   │   ├── classifier_service.py    # Protocol: classify documents
│   │   ├── scoring_service.py       # Protocol: score relevance/severity
│   │   └── notification_service.py  # Protocol: send notifications
│   └── services/                    # Domain services (pure logic)
│       ├── matching.py              # metadata_match, normalize_term
│       ├── deduplication.py         # hash computation, Deduplicator
│       ├── ranking.py               # rank_candidates, topk_ranker
│       └── normalization.py         # URL normalize, text normalize
│
├── application/                     # Capa de aplicación (use cases)
│   ├── use_cases/
│   │   ├── extract_news.py          # Use case: extracción general
│   │   ├── aras_adhoc.py            # Use case: consulta ARAS
│   │   ├── riesgos_adhoc.py         # Use case: consulta Riesgos
│   │   ├── vigilancia_weekly.py     # Use case: boletín semanal
│   │   ├── vigilancia_historical.py # Use case: análisis histórico
│   │   ├── search_external.py       # Use case: búsqueda externa
│   │   └── evaluate_sources.py      # Use case: evaluar fuentes
│   ├── services/
│   │   ├── pipeline_orchestrator.py # Orquestación LangGraph
│   │   ├── skills_engine.py         # Skills registry + execution
│   │   └── report_generator.py      # Generación de reportes
│   └── dto/
│       ├── adhoc_request.py         # DTO: parámetros de consulta adhoc
│       ├── extraction_result.py     # DTO: resultado de extracción
│       └── search_request.py        # DTO: parámetros de búsqueda
│
├── infrastructure/                  # Capa de infraestructura (adaptadores)
│   ├── connectors/
│   │   ├── rss_connector.py         # Implementa ContentFetcher para RSS
│   │   ├── http_connector.py        # Implementa ContentFetcher para HTTP
│   │   ├── browser_connector.py     # Implementa ContentFetcher para Playwright
│   │   └── pdf_connector.py         # Implementa ContentFetcher para PDF
│   ├── extractors/
│   │   ├── trafilatura_extractor.py # Implementa TextExtractor
│   │   ├── readability_extractor.py # Implementa TextExtractor
│   │   └── bs4_extractor.py         # Implementa TextExtractor
│   ├── persistence/
│   │   ├── jsonl_repository.py      # Implementa DocumentRepository (local)
│   │   ├── s3_repository.py         # Implementa DocumentRepository (S3)
│   │   └── excel_exporter.py        # Excel generation
│   ├── search_providers/
│   │   ├── arxiv_provider.py        # Implementa SearchProvider
│   │   ├── github_provider.py       # Implementa SearchProvider
│   │   └── patents_provider.py      # Implementa SearchProvider
│   ├── llm/
│   │   ├── openai_classifier.py     # Implementa ClassifierService
│   │   ├── bedrock_classifier.py    # Implementa ClassifierService
│   │   └── rules_classifier.py      # Implementa ClassifierService (keyword-based)
│   ├── catalog/
│   │   └── yaml_source_repository.py # Implementa SourceRepository
│   └── notifications/
│       ├── smtp_notifier.py         # Implementa NotificationService
│       └── sns_notifier.py          # Implementa NotificationService
│
├── interfaces/                      # Capa de interfaces (adaptadores de entrada)
│   ├── cli/
│   │   ├── main.py                  # CLI entry point (argparse)
│   │   ├── ops_cli.py               # CLI para operaciones
│   │   └── search_cli.py            # CLI para búsqueda
│   └── api/                         # Futuro: API REST
│       └── app.py
│
├── config/                          # Configuración
│   ├── settings.py                  # Settings centralizados
│   └── container.py                 # Dependency injection container
│
└── tests/                           # Tests organizados por capa
    ├── unit/
    │   ├── domain/
    │   └── application/
    ├── integration/
    │   ├── infrastructure/
    │   └── interfaces/
    └── fixtures/
```

---

## 3. Protocolos (Ports)

```python
# domain/ports/content_fetcher.py
from typing import Protocol

class ContentFetcher(Protocol):
    async def fetch(self, url: str, timeout: int = 25) -> tuple[str | None, int, str | None]:
        """Fetch content. Returns (content, status_code, error_type)."""
        ...

# domain/ports/classifier_service.py
class ClassifierService(Protocol):
    def classify(self, text: str, title: str, mode: str = "rules") -> ClassifyResult:
        """Classify document into category."""
        ...

# domain/ports/document_repository.py
class DocumentRepository(Protocol):
    def save_documents(self, documents: list[Document], out_dir: str) -> Path:
        """Save documents to storage."""
        ...
    def save_report(self, report: dict, out_dir: str) -> Path:
        """Save run report."""
        ...

# domain/ports/search_provider.py
class SearchProvider(Protocol):
    async def search(self, term: str, max_results: int = 20) -> list[SearchCandidate]:
        """Search for candidates by term."""
        ...
```

---

## 4. Plan de Migración por Fases

### Fase 1: Extraer Domain (Sprint 0-1)

**Objetivo:** Mover entidades y lógica pura a `domain/` sin romper nada.

1. Crear `domain/entities/` con Document, SourceConfig (copiar de state.py)
2. Crear `domain/value_objects/` con QueueItem, MatchResult, enums
3. Crear `domain/services/` con matching.py, deduplication.py, normalization.py
4. Crear `domain/ports/` con Protocol classes
5. Actualizar imports en el código existente para apuntar a domain/

**Riesgo:** Romper imports existentes.  
**Mitigación:** Mantener re-exports en `extractor/state.py` como aliases temporales.

### Fase 2: Extraer Infrastructure (Sprint 1-2)

**Objetivo:** Mover adaptadores a `infrastructure/`.

1. Mover connectors/ → infrastructure/connectors/ (implementan ContentFetcher)
2. Mover extract/ → infrastructure/extractors/ (implementan TextExtractor)
3. Mover report.py → infrastructure/persistence/jsonl_repository.py
4. Mover catalog.py → infrastructure/catalog/yaml_source_repository.py
5. Mover search/providers/ → infrastructure/search_providers/

### Fase 3: Crear Application Layer (Sprint 2-3)

**Objetivo:** Definir use cases con dependency injection.

1. Crear use cases: extract_news, aras_adhoc, riesgos_adhoc, etc.
2. Refactorizar graph.py → application/services/pipeline_orchestrator.py
3. Implementar container.py con DI (constructor injection)
4. Los use cases reciben ports por constructor, no importan infraestructura

### Fase 4: Refactorizar Interfaces (Sprint 3)

**Objetivo:** CLI limpio que solo instancia container y llama use cases.

1. Refactorizar main.py → interfaces/cli/main.py
2. CLI solo parsea args, crea container, llama use case
3. Preparar estructura para API REST futura

---

## 5. Reglas de Dependencia

```
interfaces → application → domain ← infrastructure
     │              │          ▲          │
     │              │          │          │
     └──────────────┴──────────┴──────────┘
                    Solo hacia domain
```

- `domain/` NO importa nada de application, infrastructure o interfaces
- `application/` importa solo de domain (ports + entities)
- `infrastructure/` implementa ports de domain
- `interfaces/` usa application (use cases) y config (container)

---

## 6. Backward Compatibility

Durante la migración:
- Mantener `extractor/` como wrapper que re-exporta desde la nueva estructura
- CLI `python -m extractor.main` sigue funcionando
- Tests existentes siguen pasando sin modificación
- Migración gradual: un módulo a la vez
