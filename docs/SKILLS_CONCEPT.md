# Capabilities & Playbooks (antes "Skills")

## Terminología

Para evitar confusión con las Kiro Skills (instrucciones para el agente AI del IDE),
el proyecto renombró "Skills-Code" → **Capabilities** y mantiene "Skills-Docs" → **Playbooks**.

| Concepto | Antes | Ahora | Ubicación |
|----------|-------|-------|-----------|
| Funciones Python reutilizables | Skills-Code | **Capabilities** | `extractor/capabilities/` |
| Instrucciones operativas .md | Skills-Docs | **Playbooks** | `playbooks/` |
| Instrucciones para el agente AI | (no existía) | **Kiro Skills** | `.kiro/skills/` |

## Capabilities (funciones Python)

Módulos Python invocables por el pipeline con contrato definido (inputs/outputs).

- **Ubicación**: `extractor/capabilities/`
- **Estructura**:
  - `capabilities/registry.py` — Registro con metadatos (`CapabilityDef`)
  - `capabilities/match.py` — Normalización + matching por metadata
  - `capabilities/ranking.py` — Interfaz para scoring/ranking (placeholder)
  - `capabilities/classify.py` — Interfaz para clasificación (placeholder)
- **Contrato**:
  ```python
  CapabilityDef(
      name="match_terms",
      purpose="Match terms against title/snippet metadata",
      inputs_schema={"title": "str", "snippet": "str", "terms": "list[str]"},
      outputs_schema={"score": "float", "matched_terms": "list[str]"},
      callable=match_terms_metadata_only,
  )
  ```
- **Uso**:
  ```python
  from extractor.capabilities import get_capability, list_capabilities

  cap = get_capability("match_terms")
  result = cap.callable("Fraude en Bancolombia", "", ["fraude"])
  ```
- **Tests**: `pytest tests/test_capabilities_match.py`

## Playbooks (instrucciones operativas)

Instrucciones en Markdown para operadores humanos o agentes.

- **Ubicación**: `playbooks/*.md`
- **Ejemplos**:
  - `ARAS_ADHOC.md` — Consulta ARAS por empresa + rango
  - `RIESGOS_ADHOC.md` — Consulta Riesgos por términos + rango
  - `VIGILANCIA_TECH.md` — Horizontes y comandos de vigilancia
  - `SOURCE_ONBOARDING.md` — Evaluar e incorporar nuevas fuentes

## Kiro Skills (instrucciones para el agente AI)

Archivos Markdown en `.kiro/skills/` que enseñan al agente de Kiro cómo
trabajar con el proyecto. Se activan automáticamente por contexto o con `/` en el chat.

- **Ubicación**: `.kiro/skills/`
- **Disponibles**:
  - `aras-adhoc-query` — Guía al agente para ejecutar consultas ARAS
  - `riesgos-adhoc-query` — Guía al agente para ejecutar consultas Riesgos

## Backward Compatibility

`extractor/skills/` sigue existiendo como shim que re-exporta desde `extractor/capabilities/`.
Los imports antiguos funcionan pero emiten `DeprecationWarning`.
