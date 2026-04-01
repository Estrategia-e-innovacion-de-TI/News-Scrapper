# News-Scrapper

Monorepo para vigilancia tecnologica, consultas ARAS/Riesgos, trend mapping, risk mapping, subscriptions y adapters SMCP/AI Agent.

## Estado actual

- `newsradar_back`: backend principal FastAPI con dominios canonicos `tech_watch`, `trend_mapping`, `subscriptions`, `aras_search` y `risk_mapping`.
- `newsradar_front`: frontend Angular 21 reorganizado en 5 tabs: `tech-watch`, `trendmap`, `subscriptions`, `aras`, `riskmap`.
- `newsradar_smcp`: adapter HTTP funcional sobre capacidades del backend. Todavia no reemplaza por completo al motor de ingesta.
- `newsradar_aiagent`: cliente opcional sobre backend/SMCP. No contiene logica core ni es parte del camino critico.
- `shared/`: configuracion declarativa prioritaria para catalogos, flujos, prompts, topicos, schedules y ejemplos de snapshots.

## Arquitectura objetivo implementada

### Backend

`newsradar_back/src/newsradar_api/`

- `domains/tech_watch`
- `domains/trend_mapping`
- `domains/subscriptions`
- `domains/aras_search`
- `domains/risk_mapping`
- `shared_kernel/config`
- `shared_kernel/documents`
- `shared_kernel/snapshots`
- `shared_kernel/observability`
- `worker`

### Persistencia

Se introdujo el modelo canónico para:

- `executions`
- `execution_sources`
- `documents`
- `document_scores`
- `document_topics`
- `report_snapshots`
- `trend_reports`
- `risk_reports`
- `subscription_topics`
- `subscription_deliveries`
- `search_audit`
- `exports_audit`
- `llm_prompts`
- `flow_configs`
- `source_catalog`
- `job_status`

Compatibilidad legacy mantenida:

- `pipeline_runs`
- `trendmap_snapshots`
- `clusters`
- `trends`
- `topics`
- rutas `/api/vigilancia/*`, `/api/pipeline/*`, `/api/riesgos/search`

## Endpoints principales

### Canonicos

- `POST /api/tech-watch/run`
- `GET /api/tech-watch/executions`
- `GET /api/tech-watch/documents`
- `GET /api/tech-watch/topics`
- `POST /api/trendmap/generate`
- `GET /api/trendmap/latest`
- `GET /api/trendmap/history`
- `GET /api/trendmap/{snapshot_id}`
- `POST /api/subscriptions`
- `GET /api/subscriptions`
- `PUT /api/subscriptions/{id}`
- `GET /api/subscriptions/deliveries`
- `POST /api/aras/search`
- `GET /api/aras/search/history`
- `GET /api/aras/search/{search_id}`
- `GET /api/aras/export/{export_id}`
- `POST /api/riskmap/run`
- `GET /api/riskmap/latest`
- `GET /api/riskmap/history`
- `GET /api/riskmap/{snapshot_id}`
- `GET /api/health`
- `GET /api/jobs/status`
- `GET /api/catalog/sources`

### Legacy mantenidos

- `POST /api/pipeline/run`
- `GET /api/pipeline/status/{run_id}`
- `GET /api/vigilancia/topics`
- `POST /api/vigilancia/subscribe`
- `POST /api/riesgos/search`
- `GET /api/trendmap/`
- `GET /api/trendmap/meta`

## Snapshots

Ejemplos incluidos en:

- `shared/examples/trendmap_snapshot.sample.json`
- `shared/examples/riskmap_snapshot.sample.json`

Los snapshots se generan en backend y quedan persistidos/versionados para consumo directo del frontend.

- analitica estructurada con vectorizacion TF-IDF, reduccion dimensional, clusterizacion y payloads de charts
- enriquecimiento opcional con LLM en Bedrock para relabeling de clusters, `executive_summary`, `insights` y `recommendations`
- trazabilidad LLM en `parameters.llm_enrichment` y persistencia de prompts en `llm_prompts`

### Metodologia v3

- documento tecnico: `docs/analytics-mapping-methodology.md`
- snapshots `version: 3`
- nuevos campos clave:
  - `methodology_version`
  - `cluster_quality`
  - `taxonomy_matches`
  - `impact_score_breakdown`
  - `maturity_score_breakdown`
  - `momentum_score_breakdown`
  - `novelty_score_breakdown`
  - `risk_severity`
  - `representative_documents`
  - `insight_evidence`
  - `quality_checks`
  - `filters_metadata`
  - `comparative_signals`

## Configuracion compartida

La resolucion de config ahora prioriza `shared/`:

- `shared/catalog.yaml`
- `shared/flows/tech_watch.yaml`
- `shared/flows/trend_mapping.yaml`
- `shared/flows/risk_mapping.yaml`
- `shared/prompts/rerank_vigilancia.yaml`
- `shared/prompts/rerank_riesgo.yaml`
- `shared/prompts/snapshot_trendmap.yaml`
- `shared/prompts/snapshot_riskmap.yaml`
- `shared/topics/tech_watch.yaml`
- `shared/schedules/default.yaml`

Fallback legado conservado:

- `newsradar_back/config/*`

## Desarrollo local

Ver [RUNBOOK.md](RUNBOOK.md).

## Docker local

`docker-compose.yml` levanta:

- `postgres`
- `backend`
- `worker`
- `smcp`
- `aiagent`
- `frontend`

Puertos:

- backend: `8000`
- frontend: `4200`
- smcp: `8080`
- aiagent: `8090`
- postgres: `5432`

## Validacion ejecutada

- `python -m pytest -q tests/test_analytics_runtime.py` en `newsradar_back` -> `5 passed`
- `python -m pytest -q` en `newsradar_aiagent` -> `3 passed`
- `python -m compileall newsradar_back/src newsradar_smcp/src newsradar_aiagent/src`

Nota:

- `ng build` no pudo ejecutarse en este entorno porque `node`/`npm` no estan disponibles en PATH.

## TODOs reales

- `newsradar_smcp` hoy es un adapter HTTP funcional al backend. La extraccion sigue corriendo desde `newsradar_back` mientras se completa la migracion del ownership de ingesta.
- `newsradar_aiagent` queda integrado pero opcional. No se recomienda invertir ahi antes de cerrar el core operativo.
- Las fuentes institucionales de riesgo quedaron catalogadas; el afinado extractor por fuente y el parsing PDF especializado sigue pendiente.
- Patentes siguen sujetas a estabilidad/credenciales externas.
- Las migraciones y el smoke con Postgres real siguen dependiendo de que Docker Desktop o un Postgres local esten disponibles.
