# Trend/Risk Mapping Audit Notes

Este documento resume la implementacion aplicada en `analytics_methodology_v5`.
La fuente de verdad sigue siendo el codigo en backend y frontend.

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
