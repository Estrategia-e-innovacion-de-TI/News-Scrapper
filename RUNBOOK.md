# Runbook local

## Script rapido en macOS / zsh

En la raiz del repo existe `run_local_newsradar.zsh`.

Permisos y ayuda:

```bash
chmod +x run_local_newsradar.zsh
./run_local_newsradar.zsh help
```

Flujo minimo sin Docker:

```bash
./run_local_newsradar.zsh bootstrap
./run_local_newsradar.zsh start-smcp
./run_local_newsradar.zsh start-backend
./run_local_newsradar.zsh generate-snapshots
./run_local_newsradar.zsh smoke
```

## 1. Stack completo con Docker

Desde la raiz:

```powershell
docker compose up --build
```

Nota:

- Docker Desktop debe estar iniciado. Si `docker info` falla, el daemon no está activo y el stack no va a levantar.
- Si quieres que los snapshots usen Bedrock en vez del fallback heurístico, exporta antes:

```powershell
$env:AWS_REGION="us-east-1"
$env:BEDROCK_MODEL_ID="anthropic.claude-3-haiku-20240307-v1:0"
$env:NEWSRADAR_SNAPSHOT_LLM_MODE="enabled"
```

Servicios esperados:

- Frontend: `http://localhost:4200`
- Backend: `http://localhost:8000`
- SMCP: `http://localhost:8080`
- AI Agent: `http://localhost:8090`
- Postgres: `localhost:5432`

## 2. Backend sin Docker

```powershell
cd newsradar_back
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
set DATABASE_URL=postgresql+asyncpg://newsradar:newsradar@localhost:5432/newsradar
uvicorn newsradar_api.main:app --reload --port 8000 --app-dir src
```

## 3. Worker local

```powershell
cd newsradar_back
.venv\Scripts\Activate.ps1
python -m newsradar_api.worker.runner
```

## 4. Frontend sin Docker

```powershell
cd newsradar_front
npm install
npm run start -- --host 0.0.0.0 --port 4200
```

## 5. SMCP sin Docker

```powershell
cd newsradar_smcp
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
set NEWSRADAR_BACK_URL=http://localhost:8000
uvicorn newsradar_server.application.app:app --reload --port 8080 --app-dir src
```

## 6. AI Agent sin Docker

```powershell
cd newsradar_aiagent
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
set NEWSRADAR_SMCP_URL=http://localhost:8080
uvicorn newsradar_agent.server:app --reload --port 8090 --app-dir src
```

## 7. Migraciones

Con Postgres disponible:

```powershell
cd newsradar_back
.venv\Scripts\Activate.ps1
alembic upgrade head
```

Chequeo offline sin Postgres:

```powershell
cd newsradar_back
.venv\Scripts\alembic.exe upgrade head --sql
```

## 8. Smoke checks

```powershell
curl http://localhost:8000/api/health
curl http://localhost:8000/api/jobs/status
curl http://localhost:8000/api/catalog/sources
curl http://localhost:8080/health
curl http://localhost:8090/health
```

Smoke reproducible con datos semilla:

```powershell
cd newsradar_back
.venv\Scripts\Activate.ps1
python scripts/seed_smoke_data.py
python scripts/smoke_stack.py --include-aiagent --expect-nonempty
```

## 9. Flujos manuales

### Vigilancia tecnologica

```powershell
curl -X POST http://localhost:8000/api/tech-watch/run -H "Content-Type: application/json" -d "{}"
curl http://localhost:8000/api/tech-watch/executions
curl http://localhost:8000/api/trendmap/latest
```

### Trend Mapping y Risk Mapping desde histórico persistido

```powershell
curl -X POST "http://localhost:8000/api/trendmap/generate" -H "Content-Type: application/json" -d "{\"window_months\":6,\"force\":true}"
curl -X POST "http://localhost:8000/api/riskmap/generate?window_months=6&force=true"
curl http://localhost:8000/api/trendmap/latest
curl http://localhost:8000/api/riskmap/latest
```

### ARAS / Riesgos ad hoc

```powershell
curl -X POST http://localhost:8000/api/aras/search -H "Content-Type: application/json" -d "{\"company\":\"Bancolombia\",\"date_from\":\"2026-03-01\",\"date_to\":\"2026-03-31\"}"
curl http://localhost:8000/api/aras/search/history
```

### Risk mapping

```powershell
curl -X POST http://localhost:8000/api/riskmap/run -H "Content-Type: application/json" -d "{}"
curl http://localhost:8000/api/riskmap/latest
```
