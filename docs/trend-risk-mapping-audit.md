# Trend/Risk Mapping Audit Notes

Este documento resume la implementacion aplicada sobre el codigo real. La fuente
de verdad sigue siendo el backend y frontend, no los README.

## Actualizacion Trend Mapping

Trend Mapping ya no usa el motor `analytics_methodology_v5` como fuente primaria.
El flujo `shared/flows/trend_mapping.yaml` selecciona
`legacy_trend_pipeline_adapter`, que adapta la logica funcional observada en
`News-Scrapper-deprecated/News-Scrapper/trendmap/scripts/build_trendmap.py` al
snapshot JSON v3 actual.

Puntos migrados/adaptados:

- Representacion: `title + excerpt/text` como en `build_trendmap.py`.
- Proyeccion: UMAP con fallback PCA cuando `umap` no esta disponible.
- Clustering: KMeans con seleccion de K por silhouette como referencia funcional,
  seguido por HDBSCAN cuando produce suficientes clusters y poco ruido.
- Fallback operativo: si HDBSCAN falta o colapsa a muy pocos clusters, el adapter
  usa KMeans por silhouette en vez de un `single_cluster`.
- Labeling: mantiene el prompt de labeling por cluster con Claude/Bedrock cuando
  hay runtime disponible y fallback lexicografico cuando no lo hay.
- Snapshot: la salida se transforma a `clusters`, `cluster_cards`, `insights`,
  `recommendations`, `risk_signals`, `quality_checks`, `filters_metadata` y
  `parameters` del contrato snapshot-driven actual.
- LLM de snapshot: queda deshabilitado para Trend desde config para no reescribir
  ni aplanar labels/insights ya generados por el flujo de analisis.

La version metodologica actual de Trend es
`deprecated_build_trendmap_adapter_v2`.

## Cambios implementados

- Ingestion batch:
  - `tech_watch` ahora puede ampliar el corpus con `google_news` y `arxiv`.
  - `risk_mapping` ahora puede ampliar el corpus con `google_news`.
  - Los resultados externos entran con `query_terms` persistidos para no perder trazabilidad de busqueda.
- Representacion documental:
  - el texto usado para clusterizar ya no inyecta `source_id`, `source_type`, `category` ni `risk_type` como parte del espacio semantico.
  - se mantiene `title + excerpt + keywords/eventos + body limpio`.
- Clusterizacion:
  - el gate de relevancia ahora admite documentos fuertes de tipo paper/report y weak signals recientes con buena señal taxonomica.
  - los documentos frontera pueden reingresar al cluster mas cercano si cumplen similitud y compatibilidad taxonomica.
- Near-duplicates:
  - la firma de duplicado ahora usa titulo, excerpt, keywords y cuerpo normalizado.
  - los documentos representativos priorizan diversidad de fuente y evitan repetir firmas casi identicas.
- Frontend snapshot-driven:
  - Trend Mapping expone filtros para `signal_state`, `comparative_status` y `novelty_band`.

## Archivos principales tocados

- `newsradar_back/src/newsradar_api/infrastructure/pipeline/nodes.py`
- `newsradar_back/src/newsradar_api/domain/model/pipeline_models.py`
- `newsradar_back/src/newsradar_api/shared_kernel/documents/persistence.py`
- `newsradar_back/src/newsradar_api/shared_kernel/analytics/advanced_engine.py`
- `shared/flows/tech_watch.yaml`
- `shared/flows/risk_mapping.yaml`
- `newsradar_front/src/app/infrastructure/noticias/services/trendmap.service.ts`
- `newsradar_front/src/app/UI/features/noticias/components/trendmap/trendmap.component.ts`
- `newsradar_front/src/app/UI/features/noticias/components/trendmap/sidebar.component.ts`

## Reuso para Risk Mapping

- La mejora de clusterizacion vive en `advanced_engine.py`, por lo que aplica a trend y risk.
- La ampliacion de fuentes batch para riesgo ya queda preparada desde `nodes.py` + `risk_mapping.yaml`.
- La siguiente iteracion deberia profundizar taxonomia de riesgos, severity/persistence y reglas de weak signals sobre corpus real.
