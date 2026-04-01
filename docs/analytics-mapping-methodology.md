# Analytics Mapping Methodology v3

## 1. Diagnostico comparativo actual vs viejo

### Developer actual

- La migracion a snapshots/backend centralizado quedo bien a nivel estructural.
- Trend Mapping perdio calidad analitica porque la semantica de clusters y varias metricas quedaron mas planas que en la implementacion vieja.
- Risk Mapping quedo funcional, pero demasiado reducido: sin una vista comparable a Trend Mapping y con menor profundidad de clusterizacion, scoring y narrativa.

### Main viejo

- Tenia mejor percepcion analitica en Trend Mapping por tres razones:
  - clustering y layout mas convincentes para lectura ejecutiva
  - narrativa/labels mas utiles para identificar por que un cluster importaba
  - UX mas rica para navegar clusters, documentos y contexto

### Que se perdio en la migracion

- labels y keywords menos curados
- insights menos aterrizados
- impacto vs madurez resuelto con heuristicas demasiado pobres
- hype cycle menos creible
- menor explicabilidad por cluster
- Risk Mapping demasiado superficial frente a Trend Mapping

### Que se recupera y mejora en v3

- representacion documental hibrida
- taxonomia configurable para trends y riesgos
- cluster_quality y quality_checks
- score breakdowns interpretables
- comparative signals entre snapshots
- weak signal detection explicita
- Risk Mapping comparable con Trend Mapping en estructura y UX

## 2. Problemas detectados en Trend Mapping

- TF-IDF solo o muy dominante empobrecia similitud y keywords.
- Cluster naming podia caer en etiquetas genericas.
- Impacto, madurez y hype dependian de reglas demasiado planas.
- La explicabilidad del cluster no mostraba suficientes razones, fuentes ni evidencia.
- El frontend no exponia bien filtros, quality checks, cluster cards ni comparative signals.

## 3. Problemas detectados en Risk Mapping

- Snapshot y UI no seguian una estructura comparable a Trend Mapping.
- Faltaban clusters de riesgo mas legibles y profundos.
- La mezcla severidad/persistencia/momentum no estaba explicitada.
- La visualizacion no permitia priorizar ni navegar riesgos con suficiente contexto.

## 4. Metodologia propuesta e implementada

### Representacion documental

- texto enriquecido por documento:
  - titulo
  - excerpt
  - texto normalizado
  - keywords previas
  - categoria/risk_type
  - metadata de fuente
- feature space hibrido:
  - TF-IDF n-gram
  - embeddings cuando hay runtime Bedrock disponible
  - features auxiliares de fuente, recencia, taxonomia, adopcion/exploracion y materialidad
- deduplicacion ligera:
  - duplicate_signature
  - duplicate_flag
  - duplicate_pressure por cluster

### Clasificacion y taxonomia

- nueva taxonomia configurable en `shared/topics/analytics_taxonomy.yaml`
- taxonomias separadas para:
  - trend categories
  - risk categories
- cada documento y cluster guarda `taxonomy_matches`
- la taxonomia alimenta:
  - clasificacion
  - naming
  - scoring
  - filtros
  - explicabilidad

### Clusterizacion

- HDBSCAN si esta disponible; KMeans fallback si no
- proyeccion 2D para coordenadas de snapshot
- ruido manejado con `sin_cluster`
- deteccion explicita de `weak_signal_flag`
- `cluster_quality` por cluster:
  - coherence
  - separation
  - taxonomy_focus
  - duplicate_pressure

### Labeling y keywords

- primero se generan terminos y labels heuristico-estadisticos desde centroides, taxonomia y documentos representativos
- despues se permite relabeling LLM controlado sobre snapshots ya estructurados
- prompts LLM reforzados para:
  - evitar nombres genericos
  - usar score/stage/taxonomia/evidencia real
  - producir insights comparativos y ejecutivos

### Scores interpretables

#### Trend Mapping

- Impacto:
  - `0.28 relevancia + 0.16 autoridad + 0.14 diversidad + 0.14 escala + 0.14 foco taxonomico + 0.14 transversalidad`
- Madurez:
  - `0.28 recurrencia + 0.20 adopcion + 0.16 escala + 0.14 coherencia + 0.12 autoridad + 0.10 baja novedad`
- Momentum:
  - `0.40 crecimiento + 0.25 aceleracion + 0.20 recencia + 0.15 visibilidad`
- Novedad:
  - `0.45 recencia + 0.30 baja recurrencia + 0.15 exploracion + 0.10 escala pequena`
- Incertidumbre:
  - `0.30 exploracion + 0.25 baja coherencia + 0.20 baja autoridad + 0.15 duplicidad + 0.10 bajo foco taxonomico`

#### Risk Mapping

- Severidad:
  - `0.26 relevancia + 0.24 materialidad + 0.18 autoridad + 0.16 diversidad + 0.16 foco taxonomico`
- Persistencia:
  - `0.40 recurrencia + 0.20 escala + 0.15 autoridad + 0.15 coherencia + 0.10 diversidad`
- Impacto:
  - `0.50 severidad + 0.20 persistencia + 0.15 diversidad + 0.15 foco taxonomico`
- Madurez de riesgo:
  - `0.45 persistencia + 0.20 autoridad + 0.20 foco taxonomico + 0.15 coherencia`

### Hype cycle operativo

- stages:
  - weak_signal
  - innovation_trigger
  - rising_attention
  - peak_visibility
  - correction
  - consolidation
  - productive_adoption
- el stage no depende solo del LLM; depende de:
  - impact_score
  - maturity_score
  - momentum_score
  - novelty_score
  - uncertainty_score
  - weak_signal_flag

### Comparative signals

- si existe snapshot previo:
  - se busca cluster similar por keywords/categoria
  - se estima status:
    - new
    - accelerating
    - cooling
    - stable
- se guardan:
  - delta_documents
  - delta_impact
  - delta_momentum
  - similarity

## 5. Cambios de backend

- `advanced_engine.py`
  - nueva representacion hibrida
  - nueva taxonomia configurable
  - score breakdowns
  - cluster_quality
  - weak signals
  - comparative metrics
- `report_builder.py`
  - snapshots `version: 3`
  - payloads trend/risk enriquecidos y comparables
  - comparative signals adjuntos al persistir
- `snapshot_enricher.py`
  - prompts LLM ahora reciben comparative signals y methodology
- `shared/prompts/snapshot_trendmap.yaml`
  - prompt reforzado para narrativa basada en evidencia
- `shared/prompts/snapshot_riskmap.yaml`
  - prompt reforzado para riesgo dominante, drivers e implicaciones

## 6. Cambios de frontend

### Trend Mapping

- overview enriquecido con:
  - cluster cards
  - taxonomy breakdown
  - volume chart
  - weak signals
  - quality checks
- sidebar con filtros reales del snapshot:
  - categoria
  - source type
  - maturity stage
  - hype stage
  - weak signals
  - orden
- detail panel con:
  - rationale
  - insight evidence
  - representative documents
  - score breakdowns
- scatter de impacto/madurez y hype cycle rehechos
- metodologia UI alineada con formulas reales del backend

### Risk Mapping

- nueva vista comparable con Trend Mapping
- filtros snapshot-driven
- mapa severidad vs momentum
- panel de cluster seleccionado
- taxonomy/source mix/temporal bars
- documentos representativos y tabla documental

## 7. Contrato de snapshots v3

Campos relevantes agregados o reforzados:

- `methodology_version`
- `cluster_quality`
- `taxonomy_matches`
- `maturity_score_breakdown`
- `impact_score_breakdown`
- `momentum_score_breakdown`
- `novelty_score_breakdown`
- `uncertainty_score_breakdown`
- `risk_severity`
- `risk_severity_breakdown`
- `persistence_score`
- `hype_stage`
- `weak_signal_flag`
- `representative_documents`
- `insight_evidence`
- `cluster_cards`
- `trend_cards`
- `quality_checks`
- `filters_metadata`
- `comparative_signals`
- `methodology`

## 8. Recalculo de snapshots

### Trend Mapping

- endpoint: `POST /api/trendmap/generate`
- lectura: `GET /api/trendmap/`

### Risk Mapping

- generar pipeline: `POST /api/riskmap/run`
- snapshot latest: `GET /api/riskmap/latest`

## 9. Validacion ejecutada

- backend:
  - `python -m pytest -q tests/test_analytics_runtime.py`
  - resultado: `5 passed`

## 10. Riesgos y trade-offs

- si no hay runtime Bedrock, el sistema cae a modo heuristico/estadistico; mejora mucho frente a v2, pero la calidad de relabeling puede bajar.
- si `node`/`npm` no estan disponibles en el entorno, no se puede ejecutar `ng build` aunque el codigo quede preparado.
- Risk Mapping ahora depende de que el snapshot backend incluya la metadata enriquecida v3; snapshots viejos pueden verse menos completos.

## 11. Pendientes reales

- correr build Angular en un entorno con Node/NPM disponible
- regenerar snapshots reales v3 y revisar calibracion con datos productivos
- si se requiere, actualizar ejemplos JSON en `shared/examples/` con snapshots reales v3
