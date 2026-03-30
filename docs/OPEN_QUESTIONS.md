# PREGUNTAS ABIERTAS — News Radar MVP

**Fecha:** 2026-03-16  
**Convención:** Cada pregunta tiene un default propuesto. Si no se resuelve, se usa el default.

---

## OQ-01: Proveedor LLM para clasificación

**Pregunta:** ¿Qué proveedor LLM usar para clasificación de categorías ARAS y tipos de riesgo?

**Opciones:**
| Opción | Pros | Contras |
|--------|------|---------|
| OpenAI GPT-4o-mini | Rápido, barato (~$0.15/1M tokens input) | Dependencia externa, datos salen del perímetro |
| AWS Bedrock (Claude Haiku) | Dentro de AWS, compliance | Requiere cuenta Bedrock, setup adicional |
| Modelo local (Ollama/vLLM) | Sin dependencia externa, datos locales | Requiere GPU o CPU potente, más lento |
| Rules-only (sin LLM) | Sin costo, determinístico, auditable | Menor precision, no captura contexto |

**Default propuesto:** Rules-only como v1 (Sprint 1), OpenAI GPT-4o-mini como v2 (Sprint 5), con flag `--classifier rules|llm`.

---

## OQ-02: Resolución NIT → Nombre de empresa

**Pregunta:** ¿Qué servicio usar para resolver NIT a nombre de empresa?

**Opciones:**
| Opción | Pros | Contras |
|--------|------|---------|
| RUES API (Cámara de Comercio) | Oficial, datos actualizados | Requiere registro, posible costo |
| Tabla local NIT→nombre | Rápido, sin dependencia | Desactualizado, mantenimiento manual |
| Input manual (usuario provee nombre) | Simple | No automatizado |

**Default propuesto:** Input manual (usuario provee nombre O NIT). Si provee NIT, se busca en tabla local. RUES API como mejora futura.

---

## OQ-03: Formato de suscripciones

**Pregunta:** ¿Cómo gestionar suscripciones de usuarios a temas de vigilancia?

**Opciones:**
| Opción | Pros | Contras |
|--------|------|---------|
| YAML local (`subscribers.yaml`) | Simple, versionable | No escala, no self-service |
| Base de datos (SQLite/DynamoDB) | Escalable, queryable | Complejidad adicional |
| API REST con UI | Self-service | Mucho desarrollo |

**Default propuesto:** YAML local para SBX PoC. Migrar a DynamoDB cuando haya UI.

---

## OQ-04: Google Patents provider

**Pregunta:** ¿Cómo resolver el problema de Google Patents (SPA/CAPTCHA)?

**Opciones:**
| Opción | Pros | Contras |
|--------|------|---------|
| SerpAPI | Confiable, structured data | Costo ($50/mes para 5000 queries) |
| Playwright scraping | Sin costo adicional | Frágil, CAPTCHA posible |
| Espacenet API (EPO) | Oficial, gratuito | Solo patentes europeas, API compleja |
| Omitir patentes en MVP | Simplifica | Pierde cobertura |

**Default propuesto:** Mantener Google Patents best-effort. Evaluar SerpAPI si el presupuesto lo permite. Espacenet como complemento para patentes EU.

---

## OQ-05: Persistencia de corpus histórico

**Pregunta:** ¿Dónde almacenar el corpus histórico para novelty scoring y trend analysis?

**Opciones:**
| Opción | Pros | Contras |
|--------|------|---------|
| JSONL acumulativo local | Simple | Crece indefinidamente, no queryable |
| SQLite local | Queryable, compacto | Requiere schema, migración |
| S3 + Athena | Escalable, serverless | Costo, complejidad |
| DuckDB local | Rápido, SQL sobre JSONL | Dependencia adicional |

**Default propuesto:** JSONL acumulativo para MVP. Migrar a DuckDB o SQLite cuando el corpus supere 100K documentos.

---

## OQ-06: Rúbrica de scoring — pesos configurables

**Pregunta:** ¿Los pesos de la rúbrica 0..100 deben ser configurables por el usuario?

**Default propuesto:** Sí, en un archivo YAML (`scoring_rubric.yaml`). Defaults: keyword_density=40%, recency=20%, source_authority=20%, topic_alignment=20%.

---

## OQ-07: Idioma de clasificación LLM

**Pregunta:** ¿En qué idioma se envían los prompts al LLM para clasificación?

**Opciones:**
- Español (match con contenido ES)
- Inglés (mejor rendimiento de modelos)
- Idioma del documento (detect_language)

**Default propuesto:** Prompts en inglés con instrucción de analizar contenido en cualquier idioma. Las categorías de salida se mantienen en español (lavado_activos, fraude, etc.).

---

## OQ-08: Límite de texto para LLM

**Pregunta:** ¿Cuánto texto enviar al LLM para clasificación?

**Default propuesto:** Título + primeros 3000 caracteres de texto. Si el modelo soporta contexto largo, enviar hasta 8000 chars. Configurable en settings.

---

## OQ-09: Frecuencia de re-evaluación de fuentes

**Pregunta:** ¿Con qué frecuencia re-evaluar fuentes existentes para detectar degradación?

**Default propuesto:** Mensual. Ejecutar `source_eval --re-evaluate` el primer día de cada mes. Alertar si una fuente Tier0 degrada a Tier2.

---

## OQ-10: Hype cycle — definición de stages

**Pregunta:** ¿Qué stages usar para el hype cycle indicator?

**Default propuesto:** Gartner-inspired simplificado:
1. `innovation_trigger` — Primeras menciones, pocos items
2. `peak_of_inflated_expectations` — Crecimiento rápido, muchos items
3. `trough_of_disillusionment` — Caída en menciones
4. `slope_of_enlightenment` — Crecimiento moderado sostenido
5. `plateau_of_productivity` — Estable, menciones constantes

Cálculo basado en: momentum (tasa de cambio de menciones en últimos 3 meses) + volumen absoluto.

---

## OQ-11: Manejo de fuentes con paywall

**Pregunta:** ¿Qué hacer con las 5 fuentes con paywall (Gartner, Forrester, Celent, VentureBeat, CISA)?

**Default propuesto:** Mantener deshabilitadas. Evaluar acceso vía:
- Newsletters gratuitas (suscripción manual, forward a inbox monitoreado)
- APIs con licencia corporativa (si disponible)
- Contenido público limitado (blogs, press releases)

No invertir en bypass de paywall.

---

## OQ-12: Formato de evidencia (citas)

**Pregunta:** ¿Qué formato usar para las citas de evidencia en el Excel?

**Default propuesto:** Fragmentos de ±150 caracteres alrededor de cada match de término, separados por `" | "`. Máximo 3 citas por documento. Formato:

```
"...fragmento con [término] resaltado..." | "...otro fragmento con [término]..."
```

---

## OQ-13: Autenticación para API REST futura

**Pregunta:** ¿Qué mecanismo de autenticación usar cuando se implemente la API REST?

**Default propuesto:** API Key simple para SBX. Migrar a Cognito/OAuth2 para producción.

---

## OQ-14: Retención de datos

**Pregunta:** ¿Cuánto tiempo retener los artifacts (JSONL, reports, Excel)?

**Default propuesto:**
- S3: 90 días para artifacts de runs individuales
- Corpus histórico: indefinido (para trend analysis)
- Run reports: 1 año
- Lifecycle policy en S3 para transición a Glacier después de 90 días

---

## OQ-15: Monitoreo y alertas

**Pregunta:** ¿Qué métricas monitorear y cuándo alertar?

**Default propuesto:**
- Alertar si: run falla, text_ok_rate < 50%, 0 documentos extraídos, duración > 30 min
- Dashboard: runs/semana, docs/run, error_rate, top fuentes por volumen
- CloudWatch métricas custom publicadas al final de cada run
