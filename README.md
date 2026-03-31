# News Radar — Monorepo

Sistema de monitoreo, clasificación y análisis de noticias para gestión de riesgos e innovación. Integra extracción automatizada de noticias, clasificación por categorías de riesgo, vigilancia tecnológica y visualización de tendencias (trend mapping).

## Estructura del Monorepo

```
Noticias/
├── newsradar_front/       # Frontend Angular 21 — Feature Noticias (Clean Architecture)
│   └── src/app/
│       ├── domain/        # Modelos y servicios de negocio
│       ├── infrastructure/# Servicios de acceso a datos/APIs
│       └── UI/            # Componentes visuales y features
├── newsradar_back/        # Backend API — Python 3.11 (Express mock / FastAPI)
│   ├── src/
│   ├── tests/
│   ├── Dockerfile
│   └── pyproject.toml
├── newsradar_smcp/        # Servidor MCP — Pipeline de extracción y clasificación
│   ├── src/
│   ├── tests/
│   ├── Dockerfile
│   └── pyproject.toml
├── newsradar_aiagent/     # Agente IA conversacional — Consultas ARAS y Riesgos
│   ├── src/
│   ├── tests/
│   ├── Dockerfile
│   └── pyproject.toml
├── shared/                # Configuración compartida entre módulos
│   ├── catalog.yaml       # Catálogo de fuentes de noticias
│   └── source_profiles.json # Perfiles de fuentes
├── .gitignore
├── MIGRATION_NOTES.md
└── README.md
```

## Requisitos Previos

| Módulo | Requisito |
|--------|-----------|
| `newsradar_front` | Node.js >= 20, npm >= 10 |
| `newsradar_back` | Python 3.11+, pip |
| `newsradar_smcp` | Python 3.11+, pip |
| `newsradar_aiagent` | Python 3.11+, pip |

## Setup e Instrucciones por Módulo

### newsradar_front — Frontend Angular 21

Frontend construido con Angular 21, TypeScript 5.9, Tailwind CSS 3.4 y D3.js v7. Sigue arquitectura Clean (domain / infrastructure / UI).

```bash
cd newsradar_front

# Instalar dependencias
npm install

# Servidor de desarrollo (http://localhost:4200)
ng serve

# Build de producción
ng build --configuration production

# Ejecutar tests unitarios
ng test

# Ejecutar tests con cobertura
npx jest --coverage
```

### newsradar_back — Backend API

Backend en Python 3.11 que expone las APIs REST consumidas por el frontend.

```bash
cd newsradar_back

# Crear entorno virtual
python3.11 -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install -e ".[dev]"

# Ejecutar servidor de desarrollo
uvicorn src.main:app --reload --port 4000

# Ejecutar tests
pytest tests/
```

### newsradar_smcp — Servidor MCP (Pipeline de Noticias)

Servidor MCP (Model Context Protocol) en Python 3.11 que ejecuta el pipeline de extracción, clasificación, scoring y exportación de noticias.

```bash
cd newsradar_smcp

# Crear entorno virtual
python3.11 -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install -e ".[dev]"

# Ejecutar servidor MCP
python -m src.server

# Ejecutar tests
pytest tests/
```

### newsradar_aiagent — Agente IA Conversacional

Agente conversacional en Python 3.11 que permite consultas de ARAS y Riesgos Emergentes mediante chat, usando boto3 y MCP.

```bash
cd newsradar_aiagent

# Crear entorno virtual
python3.11 -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install -e ".[dev]"

# Ejecutar agente
python -m src.agent

# Ejecutar tests
pytest tests/
```

## Archivos de Configuración Compartidos

La carpeta `shared/` contiene archivos de configuración utilizados por múltiples módulos:

- **`catalog.yaml`** — Catálogo de fuentes de noticias con metadatos de cada fuente (URL, frecuencia, categoría). Usado por el pipeline SMCP para la extracción.
- **`source_profiles.json`** — Perfiles detallados de cada fuente de noticias (fiabilidad, cobertura geográfica, sesgo). Usado por los módulos de clasificación y scoring.

Estos archivos se mantienen en la raíz compartida para evitar duplicación y garantizar consistencia entre módulos.

## Ejecución Completa del Sistema

Para ejecutar el sistema completo en desarrollo local:

1. Iniciar el backend: `cd newsradar_back && uvicorn src.main:app --reload --port 4000`
2. Iniciar el frontend: `cd newsradar_front && ng serve`
3. Acceder a la aplicación en `http://localhost:4200`

El frontend se conecta al backend mediante la variable de entorno `API_BASE_URL` (por defecto `http://localhost:4000/api`). Esta configuración se encuentra en `newsradar_front/src/app/config/environment.ts`.

> **Nota:** El mock_backend original en `news_radar_mvp/mock_backend/` también puede usarse como servidor de desarrollo alternativo en el puerto 4000.

## Arquitectura del Frontend (Clean Architecture)

```
newsradar_front/src/app/
├── config/                          # Tokens de inyección y entornos
│   ├── api.token.ts                 # InjectionToken API_BASE_URL
│   ├── environment.ts               # Dev: http://localhost:4000/api
│   └── environment.prod.ts          # Prod: /api
├── domain/noticias/                 # Capa de dominio (lógica de negocio)
│   ├── models/                      # Interfaces TypeScript
│   │   ├── document-result.model.ts
│   │   ├── aras.model.ts
│   │   ├── riesgos.model.ts
│   │   ├── vigilancia.model.ts
│   │   ├── trendmap.model.ts
│   │   └── index.ts                 # Barrel export
│   └── services/                    # Servicios de dominio
│       ├── riesgos.service.ts       # Validación de búsquedas
│       ├── vigilancia.service.ts    # Validación de suscripciones
│       └── trendmap.service.ts      # Filtrado, ordenamiento, agrupación
├── infrastructure/noticias/         # Capa de infraestructura (acceso a datos)
│   └── services/
│       ├── noticias-api.token.ts    # InjectionTokens y puertos (interfaces)
│       ├── riesgos-http.service.ts  # HTTP: ARAS y Riesgos Emergentes
│       ├── vigilancia-http.service.ts # HTTP: Vigilancia Tecnológica
│       └── trendmap-http.service.ts # HTTP: Trend Mapping
└── UI/                              # Capa de presentación
    ├── features/noticias/           # Feature principal
    │   ├── noticias.component.ts    # Tabs: Riesgos, Vigilancia, Trend Mapping
    │   ├── noticias.routes.ts       # Rutas lazy-loadable
    │   └── components/
    │       ├── riesgos/             # ARAS + Riesgos Emergentes + Tabla
    │       ├── vigilancia/          # Suscripción a boletín
    │       └── trendmap/            # Clusters, tendencias, D3 visualizaciones
    └── shared/components/           # Header, Footer compartidos
```

## Testing

### Frontend (Jest 30 + fast-check 4.5)

```bash
cd newsradar_front

# Tests unitarios
npx jest

# Tests con cobertura (umbral mínimo: 80%)
npx jest --coverage

# Tests en modo watch
npx jest --watch
```

Reporters configurados:
- JUnit XML → `coverage/junit.xml`
- HTML → `coverage/report-jest.html`
- Sonar → `coverage/sonar-report.xml`

### Módulos Python (pytest)

```bash
cd newsradar_back && pytest tests/
cd newsradar_smcp && pytest tests/
cd newsradar_aiagent && pytest tests/
```

## Pipelines CI/CD (Azure DevOps)

Cada módulo tiene su propio pipeline de CI:

| Módulo | Pipeline | Descripción |
|--------|----------|-------------|
| `newsradar_front` | `azure-pipeline.yml` → `pipelines/build.yml` + `pipelines/deploy.yml` | Install, lint, test, build, SonarQube, deploy |
| `newsradar_back` | `back-ci.yml` | Install, pytest con cobertura |
| `newsradar_smcp` | `smcp-ci.yml` | Install, pytest con cobertura |
| `newsradar_aiagent` | `aiagent-ci.yml` | Install, pytest con cobertura |

## Migración

Este repositorio fue migrado de Next.js 14 + React 18 a Angular 21. Para detalles completos de la migración, consultar `MIGRATION_NOTES.md`.
