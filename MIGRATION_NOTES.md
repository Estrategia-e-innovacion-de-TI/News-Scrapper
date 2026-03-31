# Notas de Migración — Refactorización del Front hacia Scaffold Angular

> Documento de seguimiento de la migración del repositorio Noticias desde Next.js 14 + React 18 hacia Angular 21 alineado con el scaffold de OPS0174001_framework_innovacion.
>
> **Requisitos relacionados:** 10.6, 11.2

---

## 1. Matriz de Compatibilidad (Referencia)

| Aspecto                | Noticias (actual)                        | framework_innovacion (objetivo)           | Brecha / Acción                                      |
|------------------------|------------------------------------------|-------------------------------------------|-------------------------------------------------------|
| Framework              | Next.js 14 + React 18                   | Angular 21                                | Migración completa de framework                       |
| Lenguaje               | TypeScript 5.4                           | TypeScript 5.9                            | Actualizar versión de TS                              |
| Estilos                | CSS modules / globals.css                | Tailwind CSS 3.4 + CSS encapsulado        | Adoptar Tailwind con paleta corporativa               |
| Arquitectura src/      | pages/ + components/ + lib/              | domain/ + infrastructure/ + UI/features/  | Reestructurar a Clean Architecture                    |
| Routing                | Next.js file-based routing               | Angular Router (app.routes.ts)            | Migrar rutas a Angular Router                         |
| Testing                | Jest 29 + fast-check 3.15                | Jest 30 + fast-check 4.5 + Playwright     | Actualizar Jest, agregar Playwright para E2E          |
| Visualización          | Plotly.js + react-plotly.js              | D3.js v7                                  | Migrar gráficos de Plotly a D3                        |
| SSR                    | Next.js SSR/SSG                          | Angular SSR (@angular/ssr)                | Configurar Angular SSR                                |
| Package Manager        | npm (package-lock.json)                  | npm (package-lock.json)                   | Compatible                                            |
| CI/CD Pipelines        | front-ci.yml (Azure Pipelines)           | azure-pipeline.yml + pipelines/           | Alinear pipelines al scaffold                         |
| Backend mock           | Express.js separado (mock_backend/)      | No aplica en scaffold                     | Mantener mock_backend como módulo independiente       |
| Paleta de colores      | Sin definir formalmente                  | Primary #FFD204, Green #00C587, etc.      | Adoptar paleta corporativa del scaffold               |
| Cobertura mínima       | Sin umbral definido                      | 80% statements/branches/functions/lines   | Configurar umbrales de cobertura                      |
| Reportes de test       | Básico (jest --verbose)                  | JUnit + HTML + Sonar                      | Agregar reporters de cobertura                        |
| Backend (SMCP)         | Python 3.11 + pydantic + scikit-learn    | N/A (solo front en scaffold)              | Mantener como módulo Python independiente             |
| Backend (AIAgent)      | Python 3.11 + boto3 + MCP               | N/A (solo front en scaffold)              | Mantener como módulo Python independiente             |

---

## 2. Archivos Movidos

| Origen | Destino | Estado | Notas |
|--------|---------|--------|-------|
| `news_radar_mvp/newsradar_back/` (25 archivos) | `newsradar_back/` | ✅ Copiado | Estructura interna preservada: Dockerfile, pyproject.toml, src/, tests/. Originales conservados como referencia. |
| `news_radar_mvp/newsradar_smcp/` | `newsradar_smcp/` | ✅ Copiado | Estructura interna preservada: Dockerfile, pyproject.toml, src/, tests/. |
| `news_radar_mvp/newsradar_aiagent/` | `newsradar_aiagent/` | ✅ Copiado | Estructura interna preservada: Dockerfile, pyproject.toml, src/, tests/. |
| `catalog.yaml`, `source_profiles.json` | `shared/` | ✅ Copiado | Archivos de configuración compartidos entre módulos. |

---

## 3. Archivos Creados

### Configuración del Proyecto Angular
| Archivo | Fase | Descripción |
|---------|------|-------------|
| `newsradar_front/angular.json` | Fase 2 | Configuración del workspace Angular 21 |
| `newsradar_front/package.json` | Fase 2 | Dependencias: Angular 21, D3 v7, Tailwind 3.4, Jest 30, fast-check 4.5 |
| `newsradar_front/tsconfig.json` | Fase 2 | TypeScript 5.9 en modo strict con Angular compiler options |
| `newsradar_front/tsconfig.app.json` | Fase 2 | Configuración TS para la aplicación |
| `newsradar_front/tsconfig.spec.json` | Fase 2 | Configuración TS para tests |
| `newsradar_front/jest.config.js` | Fase 2 | Jest 30 + jest-preset-angular, cobertura 80%, reporters JUnit/HTML/Sonar |
| `newsradar_front/tailwind.config.js` | Fase 2 | Tailwind CSS 3.4 con paleta corporativa |
| `newsradar_front/postcss.config.js` | Fase 2 | PostCSS para Tailwind |
| `newsradar_front/setup-jest.ts` | Fase 2 | Setup de Jest para Angular |
| `newsradar_front/.editorconfig` | Fase 2 | Configuración de editor |
| `newsradar_front/.npmrc` | Fase 2 | Configuración de npm |

### Archivos de Entrada y SSR
| Archivo | Fase | Descripción |
|---------|------|-------------|
| `newsradar_front/src/main.ts` | Fase 2 | Punto de entrada del cliente |
| `newsradar_front/src/main.server.ts` | Fase 2 | Punto de entrada del servidor SSR |
| `newsradar_front/src/server.ts` | Fase 2 | Servidor Express para SSR |
| `newsradar_front/src/index.html` | Fase 2 | HTML principal |
| `newsradar_front/src/styles.css` | Fase 2 | Estilos globales con Tailwind directives |

### Configuración de la App
| Archivo | Fase | Descripción |
|---------|------|-------------|
| `newsradar_front/src/app/app.config.ts` | Fase 2 | Providers: Router, HttpClient, Hydration, API_BASE_URL, servicios HTTP |
| `newsradar_front/src/app/app.config.server.ts` | Fase 2 | Configuración del servidor SSR |
| `newsradar_front/src/app/app.routes.ts` | Fase 2 | Rutas principales con lazy loading de Noticias |
| `newsradar_front/src/app/app.routes.server.ts` | Fase 2 | Rutas del servidor SSR |
| `newsradar_front/src/app/app.component.ts` | Fase 2 | Componente raíz con Header, Footer, RouterOutlet |
| `newsradar_front/src/app/config/api.token.ts` | Fase 2 | InjectionToken API_BASE_URL |
| `newsradar_front/src/app/config/environment.ts` | Fase 2 | Entorno dev: apiBaseUrl `http://localhost:4000/api` |
| `newsradar_front/src/app/config/environment.prod.ts` | Fase 2 | Entorno prod: apiBaseUrl `/api` |

### Capa de Dominio
| Archivo | Fase | Descripción |
|---------|------|-------------|
| `src/app/domain/noticias/models/document-result.model.ts` | Fase 3 | Interface DocumentResult |
| `src/app/domain/noticias/models/aras.model.ts` | Fase 3 | Interfaces ArasSearchRequest/Response |
| `src/app/domain/noticias/models/riesgos.model.ts` | Fase 3 | Interfaces RiesgosSearchRequest/Response, RiesgosPreset |
| `src/app/domain/noticias/models/vigilancia.model.ts` | Fase 3 | Interfaces TopicItem, SubscribeRequest/Response |
| `src/app/domain/noticias/models/trendmap.model.ts` | Fase 3 | Interfaces Cluster, Trend, HypeStage |
| `src/app/domain/noticias/models/index.ts` | Fase 3 | Barrel export de todos los modelos |
| `src/app/domain/noticias/services/riesgos.service.ts` | Fase 3 | Validación de búsquedas ARAS y Riesgos |
| `src/app/domain/noticias/services/vigilancia.service.ts` | Fase 3 | Validación de suscripciones |
| `src/app/domain/noticias/services/trendmap.service.ts` | Fase 3 | Ordenamiento, filtrado, agrupación, color-coding |

### Capa de Infraestructura
| Archivo | Fase | Descripción |
|---------|------|-------------|
| `src/app/infrastructure/noticias/services/noticias-api.token.ts` | Fase 3b | InjectionTokens y puertos (interfaces) |
| `src/app/infrastructure/noticias/services/riesgos-http.service.ts` | Fase 3b | HTTP service para ARAS y Riesgos |
| `src/app/infrastructure/noticias/services/vigilancia-http.service.ts` | Fase 3b | HTTP service para Vigilancia |
| `src/app/infrastructure/noticias/services/trendmap-http.service.ts` | Fase 3b | HTTP service para Trendmap |

### Capa UI — Feature Noticias
| Archivo | Fase | Descripción |
|---------|------|-------------|
| `src/app/UI/features/noticias/noticias.component.ts` | Fase 4 | Componente principal con tabs |
| `src/app/UI/features/noticias/noticias.routes.ts` | Fase 4 | Rutas hijas lazy-loadable |
| `src/app/UI/features/noticias/components/riesgos/riesgos.component.ts` | Fase 4 | Contenedor Riesgos con sub-tabs |
| `src/app/UI/features/noticias/components/riesgos/aras-search-form.component.ts` | Fase 4 | Formulario ARAS |
| `src/app/UI/features/noticias/components/riesgos/riesgos-search-form.component.ts` | Fase 4 | Formulario Riesgos Emergentes |
| `src/app/UI/features/noticias/components/riesgos/results-table.component.ts` | Fase 4 | Tabla de resultados |
| `src/app/UI/features/noticias/components/vigilancia/vigilancia.component.ts` | Fase 4b | Contenedor Vigilancia |
| `src/app/UI/features/noticias/components/vigilancia/subscription-form.component.ts` | Fase 4b | Formulario de suscripción |
| `src/app/UI/features/noticias/components/trendmap/trendmap.component.ts` | Fase 4c | Contenedor Trend Mapping |
| `src/app/UI/features/noticias/components/trendmap/cluster-card.component.ts` | Fase 4c | Tarjeta de cluster |
| `src/app/UI/features/noticias/components/trendmap/cluster-list.component.ts` | Fase 4c | Lista filtrable de clusters |
| `src/app/UI/features/noticias/components/trendmap/trend-list.component.ts` | Fase 4c | Lista de tendencias con color-coding |
| `src/app/UI/features/noticias/components/trendmap/d3-scatter.component.ts` | Fase 4c | Scatter plot D3.js (reemplaza Plotly) |
| `src/app/UI/features/noticias/components/trendmap/hype-cycle.component.ts` | Fase 4c | Hype cycle D3.js (reemplaza Plotly) |
| `src/app/UI/features/noticias/components/trendmap/momentum-bar.component.ts` | Fase 4c | Barra de momentum SVG |
| `src/app/UI/shared/components/header/header.component.ts` | Fase 4 | Header compartido |
| `src/app/UI/shared/components/footer/footer.component.ts` | Fase 4 | Footer compartido |

### Pipelines CI/CD
| Archivo | Fase | Descripción |
|---------|------|-------------|
| `newsradar_front/azure-pipeline.yml` | Fase 5 | Pipeline CI principal del front — referencia build.yml y deploy.yml |
| `newsradar_front/pipelines/build.yml` | Fase 5 | Pipeline de build: install, lint, test con cobertura, SonarQube, ng build |
| `newsradar_front/pipelines/deploy.yml` | Fase 5 | Pipeline de deploy: compress, publish artifact a Artifactory |
| `newsradar_back/back-ci.yml` | Fase 5 | Pipeline CI del backend Python: install, pytest con cobertura |
| `newsradar_smcp/smcp-ci.yml` | Fase 5 | Pipeline CI de SMCP Python: install, pytest con cobertura |
| `newsradar_aiagent/aiagent-ci.yml` | Fase 5 | Pipeline CI de AIAgent Python: install, pytest con cobertura |

### Documentación y Scripts
| Archivo | Fase | Descripción |
|---------|------|-------------|
| `MIGRATION_NOTES.md` | Fase 0 | Notas de migración (este archivo) |
| `README.md` | Fase 1 | Documentación del monorepo |
| `.gitignore` | Fase 1 | Patrones de exclusión para todos los módulos |
| `scripts/inventory.sh` | Fase 0 | Script de inventario de línea base |
| `inventory_baseline.txt` | Fase 0 | Inventario generado |

---

## 4. Archivos Eliminados

| Archivo | Razón | Fase |
|---------|-------|------|
| Ninguno | Los archivos originales en `news_radar_mvp/` se conservan como referencia durante la transición. Se recomienda eliminarlos una vez validada la migración completa. | — |

---

## 5. Dependencias Actualizadas

### Dependencias Eliminadas (React/Next.js → Angular)
| Dependencia | Versión Anterior | Tipo | Razón |
|-------------|-----------------|------|-------|
| `next` | ^14.2.0 | prod | Reemplazado por Angular 21 |
| `react` | ^18.3.0 | prod | Reemplazado por Angular 21 |
| `react-dom` | ^18.3.0 | prod | Reemplazado por Angular 21 |
| `plotly.js` | ^3.4.0 | prod | Reemplazado por D3.js v7 |
| `react-plotly.js` | ^2.6.0 | prod | Reemplazado por D3.js v7 |
| `pg` | ^8.20.0 | prod | No necesario en el frontend Angular |
| `@testing-library/react` | ^16.1.0 | dev | Reemplazado por jest-preset-angular |
| `@testing-library/jest-dom` | ^6.6.3 | dev | Reemplazado por jest-preset-angular |
| `identity-obj-proxy` | ^3.0.0 | dev | No necesario con Tailwind CSS |

### Dependencias Nuevas (Angular)
| Dependencia | Versión Nueva | Tipo | Notas |
|-------------|---------------|------|-------|
| `@angular/core` | ^21.1.0 | prod | Framework principal |
| `@angular/common` | ^21.1.0 | prod | Módulos comunes (HttpClient, etc.) |
| `@angular/compiler` | ^21.1.0 | prod | Compilador de templates |
| `@angular/forms` | ^21.1.0 | prod | Reactive Forms |
| `@angular/platform-browser` | ^21.1.0 | prod | Plataforma browser |
| `@angular/platform-server` | ^21.1.0 | prod | SSR |
| `@angular/router` | ^21.1.0 | prod | Router con lazy loading |
| `@angular/ssr` | ^21.1.4 | prod | Server-Side Rendering |
| `d3` | ^7.9.0 | prod | Visualizaciones (reemplaza Plotly) |
| `rxjs` | ~7.8.0 | prod | Programación reactiva |
| `tslib` | ^2.3.0 | prod | Helpers de TypeScript |
| `zone.js` | ^0.16.1 | prod | Change detection de Angular |
| `express` | ^5.1.0 | prod | Servidor SSR |
| `tailwindcss` | ^3.4.19 | dev | Framework CSS (reemplaza CSS modules) |
| `jest-preset-angular` | ^16.1.1 | dev | Preset de Jest para Angular |
| `jest-junit` | ^16.0.0 | dev | Reporter JUnit XML |
| `jest-html-reporters` | ^3.1.7 | dev | Reporter HTML |
| `jest-sonar` | ^0.2.16 | dev | Reporter Sonar |
| `@types/d3` | ^7.4.3 | dev | Tipos para D3.js |

### Dependencias Actualizadas
| Dependencia | Versión Anterior | Versión Nueva | Tipo | Notas |
|-------------|-----------------|---------------|------|-------|
| `typescript` | ^5.4.0 | ~5.9.2 | dev | Requerido por Angular 21 |
| `jest` | ^29.7.0 | ^30.2.0 | dev | Alineado con scaffold |
| `jest-environment-jsdom` | ^29.7.0 | ^30.2.0 | dev | Alineado con Jest 30 |
| `fast-check` | ^3.15.0 | ^4.5.3 | dev | Alineado con scaffold |
| `@types/jest` | ^29.5.0 | ^30.0.0 | dev | Alineado con Jest 30 |

---

## 6. Brechas Identificadas

| ID | Brecha | Severidad | Acción Requerida | Estado |
|----|--------|-----------|------------------|--------|
| B1 | CSV download no migrado | Baja | El React `ResultsTable` incluye descarga CSV client-side. El Angular `ResultsTableComponent` no la incluye aún. Agregar funcionalidad de descarga CSV. | Pendiente |
| B2 | Excel download link no migrado | Baja | El React `ResultsTable` muestra link de descarga Excel cuando `excel_url` está disponible. Agregar al componente Angular. | Pendiente |
| B3 | ChatWidget no migrado | Media | El React frontend incluye `ChatWidget.tsx` para chat con el AIAgent. No se migró al Angular ya que no estaba en el alcance del feature Noticias. | Fuera de alcance |
| B4 | PipelinePanel no migrado | Baja | El React frontend incluye `PipelinePanel.tsx` para ejecutar pipelines. No se migró al Angular. | Fuera de alcance |
| B5 | Vistas avanzadas de Trendmap no migradas | Media | React incluye vistas adicionales: VistaDetalle, VistaHype, VistaImpacto, VistaMapa, VistaMetodologia, VistaResumen, TrendmapSidebar. Estas vistas avanzadas no se migraron. | Pendiente |
| B6 | Tests unitarios y de propiedades pendientes | Media | Los tests marcados con `*` en el plan de tareas (6.3, 6.5, 6.7-6.10, 7.5, 9.7-9.10, 10.3-10.4, 11.8) están pendientes de implementación. Requieren `npm install`. | Pendiente |
| B7 | E2E tests con Playwright no configurados | Baja | El scaffold incluye Playwright para E2E pero no se configuró en esta fase. | Pendiente |
| B8 | SMCP y AIAgent sin tests ejecutables | Baja | Ambos módulos solo tienen `__init__.py` en sus carpetas de tests. | Preexistente |

---

## 7. Checklist de Validación

### 7.1 Build y Compilación
- [x] TypeScript compila sin errores en modo strict — 30+ archivos verificados con cero diagnósticos
- [ ] Build de producción (`ng build --configuration production`) — Requiere `npm install`
- [x] `newsradar_back` — Estructura migrada correctamente, Dockerfile y pyproject.toml presentes
- [x] `newsradar_smcp` — Estructura migrada correctamente, Dockerfile y pyproject.toml presentes
- [x] `newsradar_aiagent` — Estructura migrada correctamente, Dockerfile y pyproject.toml presentes

### 7.2 Tests
- [ ] Tests unitarios del front pasando — Requiere `npm install` para ejecutar
- [ ] Tests de propiedades (fast-check) pasando — Requiere `npm install` para ejecutar
- [x] Configuración de cobertura >= 80% en statements, branches, functions, lines — Verificado en `jest.config.js`
- [x] Reporters configurados: JUnit XML, HTML, Sonar — Verificado en `jest.config.js`
- [x] `newsradar_smcp` tests — No hay tests ejecutables (solo `__init__.py`)
- [x] `newsradar_aiagent` tests — No hay tests ejecutables (solo `__init__.py`)

### 7.3 Estructura y Arquitectura
- [x] Monorepo con 4 carpetas de primer nivel: `newsradar_front/`, `newsradar_back/`, `newsradar_smcp/`, `newsradar_aiagent/`
- [x] Carpeta `shared/` con `catalog.yaml` y `source_profiles.json`
- [x] Clean Architecture: `domain/noticias/models/`, `domain/noticias/services/`, `infrastructure/noticias/services/`, `UI/features/noticias/`
- [x] Standalone components con Angular signals
- [x] Lazy loading de rutas configurado
- [x] ViewEncapsulation.Emulated en NoticiasComponent

### 7.4 Rutas y Navegación
- [x] `/noticias` → redirect a `/noticias/riesgos`
- [x] `/noticias/riesgos` → RiesgosComponent con sub-tabs ARAS y Riesgos Emergentes
- [x] `/noticias/vigilancia` → VigilanciaComponent con formulario de suscripción
- [x] `/noticias/trendmap` → TrendmapComponent con clusters, tendencias y visualizaciones D3
- [x] Wildcard `**` → redirect a `/noticias`
- [x] `NOTICIAS_ROUTE_PREFIX` InjectionToken para integración futura con informe-tendencias

### 7.5 Paridad Funcional
- [x] Riesgos — ARAS: formulario con empresa, NIT, categoría, fechas, clasificador
- [x] Riesgos — Emergentes: formulario con términos, preset (5 opciones), fechas
- [x] Riesgos — Tabla de resultados con 7 columnas (Título, Medio, Fecha, Categoría, Severidad, Evidencia, URL)
- [x] Vigilancia — Carga de temas, formulario de suscripción, confirmación
- [x] Trend Mapping — Cluster cards, filtrado por categoría, ordenamiento por impacto
- [x] Trend Mapping — Trend list con color-coding por dirección, agrupación por madurez
- [x] Trend Mapping — D3 scatter plot y hype cycle (reemplazan Plotly)
- [x] Trend Mapping — Momentum bars

### 7.6 Integración Backend
- [x] `API_BASE_URL` InjectionToken configurado en `app.config.ts`
- [x] `environment.ts` apunta a `http://localhost:4000/api` (mock_backend)
- [x] `environment.prod.ts` apunta a `/api` (proxy nginx)
- [x] Servicios HTTP inyectan `API_BASE_URL` correctamente
- [x] InjectionTokens `RIESGOS_API`, `VIGILANCIA_API`, `TRENDMAP_API` registrados en `app.config.ts`

### 7.7 Pipelines CI/CD
- [x] `newsradar_front/azure-pipeline.yml` — Pipeline principal referencia build.yml y deploy.yml
- [x] `newsradar_front/pipelines/build.yml` — Install, lint, test, build, SonarQube
- [x] `newsradar_front/pipelines/deploy.yml` — Compress, publish artifact
- [x] `newsradar_back/back-ci.yml` — Pipeline CI Python
- [x] `newsradar_smcp/smcp-ci.yml` — Pipeline CI Python
- [x] `newsradar_aiagent/aiagent-ci.yml` — Pipeline CI Python

---

## 8. Resultados de Tests Post-Migración

### newsradar_smcp
- **Estado:** ⚠️ No hay archivos de test ejecutables
- **Detalle:** El directorio `newsradar_smcp/tests/` solo contiene `__init__.py` con un docstring (`"""Tests for newsradar_smcp."""`). No existen archivos de test (`test_*.py`) que ejecutar con pytest.
- **Acción:** No se ejecutó pytest ya que no hay tests definidos. Cuando se agreguen tests al módulo SMCP, se deberá verificar que pasan correctamente.
- **Requisitos:** 8.3, 10.3

### newsradar_aiagent
- **Estado:** ⚠️ No hay archivos de test ejecutables
- **Detalle:** El directorio `newsradar_aiagent/tests/` solo contiene `__init__.py` con un docstring (`"""Tests for newsradar_aiagent."""`). No existen archivos de test (`test_*.py`) que ejecutar con pytest.
- **Acción:** No se ejecutó pytest ya que no hay tests definidos. Cuando se agreguen tests al módulo AIAgent, se deberá verificar que pasan correctamente.
- **Requisitos:** 8.3, 10.4

---

*Última actualización: Fase 7 — Tareas 16.1, 16.2 — Reporte final de migración*
