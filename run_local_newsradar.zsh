#!/usr/bin/env zsh

set -euo pipefail

SCRIPT_DIR=${0:A:h}
REPO_DIR="${NEWSRADAR_REPO_DIR:-$SCRIPT_DIR}"

DB_NAME="${DB_NAME:-newsradar}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-newsradar}"
DB_PASSWORD="${DB_PASSWORD:-newsradar}"
DB_ADMIN_USER="${DB_ADMIN_USER:-$DB_USER}"
DB_ADMIN_PASSWORD="${DB_ADMIN_PASSWORD:-$DB_PASSWORD}"
DB_ADMIN_DB="${DB_ADMIN_DB:-postgres}"
DB_SCHEMA="${DB_SCHEMA:-public}"
DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}}"

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
NEWSRADAR_BACK_URL="${NEWSRADAR_BACK_URL:-$BACKEND_URL}"
NEWSRADAR_SMCP_URL="${NEWSRADAR_SMCP_URL:-http://localhost:8080}"
AIAGENT_URL="${AIAGENT_URL:-http://localhost:8090}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:4200}"

BACKEND_DIR="$REPO_DIR/newsradar_back"
SMCP_DIR="$REPO_DIR/newsradar_smcp"
AIAGENT_DIR="$REPO_DIR/newsradar_aiagent"
FRONTEND_DIR="$REPO_DIR/newsradar_front"

function log() {
  print -P "%F{cyan}==>%f $*"
}

function fail() {
  print -P "%F{red}ERROR:%f $*" >&2
  exit 1
}

function ensure_command() {
  local command_name="$1"
  command -v "$command_name" >/dev/null 2>&1 || fail "No encuentro '$command_name' en PATH."
}

function ensure_dir() {
  local path="$1"
  [[ -d "$path" ]] || fail "No existe el directorio: $path"
}

function venv_python() {
  local target_dir="$1"
  if [[ -x "$target_dir/.venv/bin/python" ]]; then
    print -- "$target_dir/.venv/bin/python"
    return
  fi
  if command -v python3.11 >/dev/null 2>&1; then
    print -- "python3.11"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    print -- "python3"
    return
  fi
  fail "No encuentro python3.11 ni python3."
}

function create_venv_if_missing() {
  local target_dir="$1"
  local python_bin
  python_bin=$(venv_python "$target_dir")
  if [[ ! -x "$target_dir/.venv/bin/python" ]]; then
    log "Creando virtualenv en $target_dir/.venv"
    (cd "$target_dir" && "$python_bin" -m venv .venv)
  fi
}

function install_backend() {
  ensure_dir "$BACKEND_DIR"
  create_venv_if_missing "$BACKEND_DIR"
  log "Instalando dependencias del backend"
  (cd "$BACKEND_DIR" && ./.venv/bin/python -m pip install -e '.[dev]')
}

function install_smcp() {
  ensure_dir "$SMCP_DIR"
  create_venv_if_missing "$SMCP_DIR"
  log "Instalando dependencias de SMCP"
  (cd "$SMCP_DIR" && ./.venv/bin/python -m pip install -e '.[dev]')
}

function install_aiagent() {
  ensure_dir "$AIAGENT_DIR"
  create_venv_if_missing "$AIAGENT_DIR"
  log "Instalando dependencias de AI Agent"
  (cd "$AIAGENT_DIR" && ./.venv/bin/python -m pip install -e '.[dev]')
}

function install_frontend() {
  ensure_dir "$FRONTEND_DIR"
  ensure_command npm
  log "Instalando dependencias del frontend"
  (cd "$FRONTEND_DIR" && npm install)
}

function maybe_start_postgres_service() {
  if command -v brew >/dev/null 2>&1; then
    if brew services list 2>/dev/null | grep -q 'postgresql@16'; then
      log "Asegurando servicio postgresql@16"
      brew services start postgresql@16 >/dev/null
      return
    fi
    if brew services list 2>/dev/null | grep -q '^postgresql '; then
      log "Asegurando servicio postgresql"
      brew services start postgresql >/dev/null
      return
    fi
  fi
  log "No intento iniciar Postgres por brew. Asegura que localhost:5432 este disponible."
}

function app_pg_env() {
  if [[ -n "${DB_PASSWORD}" ]]; then
    export PGPASSWORD="$DB_PASSWORD"
  else
    unset PGPASSWORD
  fi
}

function admin_pg_env() {
  if [[ -n "${DB_ADMIN_PASSWORD}" ]]; then
    export PGPASSWORD="$DB_ADMIN_PASSWORD"
  else
    unset PGPASSWORD
  fi
}

function reset_db() {
  ensure_command psql
  ensure_command dropdb
  ensure_command createdb
  maybe_start_postgres_service
  admin_pg_env
  log "Reseteando base de datos '$DB_NAME'"
  psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_ADMIN_USER" -d "$DB_ADMIN_DB" -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();" >/dev/null 2>&1 || true
  dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_ADMIN_USER" --if-exists "$DB_NAME"
  createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_ADMIN_USER" -O "$DB_USER" "$DB_NAME"
  psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_ADMIN_USER" -d "$DB_NAME" -c 'CREATE EXTENSION IF NOT EXISTS pgcrypto;'
}

function repair_db_permissions() {
  ensure_command psql
  maybe_start_postgres_service
  admin_pg_env
  log "Reparando permisos de '$DB_NAME' en esquema '$DB_SCHEMA' para el rol '$DB_USER'"
  psql -v ON_ERROR_STOP=1 -h "$DB_HOST" -p "$DB_PORT" -U "$DB_ADMIN_USER" -d "$DB_NAME" <<SQL
GRANT CONNECT ON DATABASE "$DB_NAME" TO "$DB_USER";
GRANT USAGE, CREATE ON SCHEMA "$DB_SCHEMA" TO "$DB_USER";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA "$DB_SCHEMA" TO "$DB_USER";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA "$DB_SCHEMA" TO "$DB_USER";
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA "$DB_SCHEMA" TO "$DB_USER";
ALTER DEFAULT PRIVILEGES FOR ROLE "$DB_ADMIN_USER" IN SCHEMA "$DB_SCHEMA" GRANT ALL PRIVILEGES ON TABLES TO "$DB_USER";
ALTER DEFAULT PRIVILEGES FOR ROLE "$DB_ADMIN_USER" IN SCHEMA "$DB_SCHEMA" GRANT ALL PRIVILEGES ON SEQUENCES TO "$DB_USER";
ALTER DEFAULT PRIVILEGES FOR ROLE "$DB_ADMIN_USER" IN SCHEMA "$DB_SCHEMA" GRANT ALL PRIVILEGES ON FUNCTIONS TO "$DB_USER";
SQL
  cat <<EOF

Permisos reparados.

Rol de aplicacion:
  $DB_USER

Rol admin usado para el repair:
  $DB_ADMIN_USER

Base/esquema:
  $DB_NAME / $DB_SCHEMA

EOF
}

function migrate_db() {
  install_backend
  log "Ejecutando migraciones Alembic"
  (
    cd "$BACKEND_DIR"
    export DATABASE_URL
    ./.venv/bin/alembic upgrade head
  )
}

function seed_smoke() {
  install_backend
  log "Cargando datos semilla para smoke"
  (
    cd "$BACKEND_DIR"
    export DATABASE_URL
    ./.venv/bin/python scripts/seed_smoke_data.py
  )
}

function seed_demo() {
  install_backend
  log "Cargando datos demo completos"
  (
    cd "$BACKEND_DIR"
    export DATABASE_URL
    ./.venv/bin/python scripts/seed.py
  )
}

function reset_full() {
  reset_db
  migrate_db
  cat <<EOF

Reset completo terminado.

Base recreada y migrada contra:
  $DATABASE_URL

Si quieres cargar datos:
  ./run_local_newsradar.zsh seed-smoke
  ./run_local_newsradar.zsh seed-demo

EOF
}

function reset_full_smoke() {
  reset_db
  migrate_db
  seed_smoke
}

function reset_full_demo() {
  reset_db
  seed_demo
}

function start_backend() {
  install_backend
  log "Arrancando backend en $BACKEND_URL"
  (
    cd "$BACKEND_DIR"
    export DATABASE_URL
    export BACKEND_URL
    export NEWSRADAR_BACK_URL
    export NEWSRADAR_SMCP_URL
    export AIAGENT_URL
    exec ./.venv/bin/uvicorn newsradar_api.main:app --reload --app-dir src --port 8000
  )
}

function start_smcp() {
  install_smcp
  log "Arrancando SMCP en $NEWSRADAR_SMCP_URL"
  (
    cd "$SMCP_DIR"
    export NEWSRADAR_BACK_URL
    exec ./.venv/bin/uvicorn newsradar_server.application.app:app --reload --app-dir src --port 8080
  )
}

function start_aiagent() {
  install_aiagent
  log "Arrancando AI Agent en $AIAGENT_URL"
  (
    cd "$AIAGENT_DIR"
    export NEWSRADAR_SMCP_URL
    export NEWSRADAR_BACK_URL
    exec ./.venv/bin/uvicorn newsradar_agent.server:app --reload --app-dir src --port 8090
  )
}

function start_frontend() {
  install_frontend
  log "Arrancando frontend en $FRONTEND_URL"
  (
    cd "$FRONTEND_DIR"
    exec npm run start -- --host 0.0.0.0 --port 4200
  )
}

function smoke() {
  install_backend
  log "Ejecutando smoke stack"
  (
    cd "$BACKEND_DIR"
    export DATABASE_URL
    local args=(scripts/smoke_stack.py --expect-nonempty)
    if [[ "${INCLUDE_AIAGENT:-0}" == "1" ]]; then
      args+=(--include-aiagent)
    fi
    ./.venv/bin/python "${args[@]}"
  )
}

function generate_snapshots() {
  ensure_command curl
  log "Generando snapshot trendmap"
  curl -sS -X POST "$BACKEND_URL/api/trendmap/generate" \
    -H 'Content-Type: application/json' \
    -d '{"window_months":6,"force":true}'
  print
  log "Generando snapshot riskmap"
  curl -sS -X POST "$BACKEND_URL/api/riskmap/generate?window_months=6&force=true"
  print
}

function real_run() {
  ensure_command curl
  log "Disparando tech watch"
  curl -sS -X POST "$BACKEND_URL/api/tech-watch/run" \
    -H 'Content-Type: application/json' \
    -d '{"days":7,"classifier_mode":"rules","max_items_per_source":20}'
  print
  log "Disparando risk mapping"
  curl -sS -X POST "$BACKEND_URL/api/riskmap/run" \
    -H 'Content-Type: application/json' \
    -d '{"days":7,"window_months":6,"classifier_mode":"rules","force_snapshot":true}'
  print
}

function health() {
  ensure_command curl
  log "Backend"
  curl -sS "$BACKEND_URL/api/health"
  print
  log "Jobs"
  curl -sS "$BACKEND_URL/api/jobs/status"
  print
  log "SMCP"
  curl -sS "$NEWSRADAR_SMCP_URL/health"
  print
  log "AI Agent"
  curl -sS "$AIAGENT_URL/health"
  print
}

function bootstrap() {
  reset_db
  migrate_db
  seed_smoke
  cat <<EOF

Bootstrap completado.

Abre terminales separadas y ejecuta:
  ./run_local_newsradar.zsh start-smcp
  ./run_local_newsradar.zsh start-backend
  ./run_local_newsradar.zsh start-aiagent   # opcional
  ./run_local_newsradar.zsh start-frontend  # opcional

Luego puedes correr:
  ./run_local_newsradar.zsh health
  ./run_local_newsradar.zsh generate-snapshots
  ./run_local_newsradar.zsh smoke

EOF
}

function usage() {
  cat <<EOF
Uso: ./run_local_newsradar.zsh <comando>

Comandos:
  bootstrap            Resetea DB, migra y carga datos semilla
  reset-db             Borra la base anterior y la recrea
  reset-full           Borra la base, la recrea y corre migraciones
  reset-full-smoke     Reset completo + datos semilla de smoke
  reset-full-demo      Reset completo + dataset demo completo
  repair-db-permissions Repara grants sobre tablas, secuencias y defaults
  migrate-db           Ejecuta alembic upgrade head
  seed-smoke           Inserta datos semilla para smoke
  seed-demo            Inserta dataset demo completo con scripts/seed.py
  setup-backend        Crea venv e instala backend
  setup-smcp           Crea venv e instala smcp
  setup-aiagent        Crea venv e instala aiagent
  setup-frontend       Instala dependencias del frontend
  start-backend        Arranca FastAPI backend en :8000
  start-smcp           Arranca SMCP en :8080
  start-aiagent        Arranca AI Agent en :8090
  start-frontend       Arranca Angular en :4200
  health               Consulta health/status de servicios
  generate-snapshots   Genera trendmap y riskmap desde historico persistido
  real-run             Dispara ingesta real de tech watch y risk mapping
  smoke                Ejecuta scripts/smoke_stack.py

Variables utiles:
  DB_NAME=$DB_NAME
  DB_HOST=$DB_HOST
  DB_PORT=$DB_PORT
  DB_USER=$DB_USER
  DB_PASSWORD=${DB_PASSWORD:+***}
  DB_ADMIN_USER=$DB_ADMIN_USER
  DB_ADMIN_PASSWORD=${DB_ADMIN_PASSWORD:+***}
  DB_ADMIN_DB=$DB_ADMIN_DB
  DB_SCHEMA=$DB_SCHEMA
  DATABASE_URL=$DATABASE_URL
  BACKEND_URL=$BACKEND_URL
  NEWSRADAR_SMCP_URL=$NEWSRADAR_SMCP_URL
  AIAGENT_URL=$AIAGENT_URL
  NEWSRADAR_REPO_DIR=$REPO_DIR

Bedrock opcional:
  export AWS_REGION=us-east-1
  export BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
  export NEWSRADAR_SNAPSHOT_LLM_MODE=enabled
  export AWS_PROFILE=tu-perfil

EOF
}

case "${1:-help}" in
  bootstrap) bootstrap ;;
  reset-db) reset_db ;;
  reset-full) reset_full ;;
  reset-full-smoke) reset_full_smoke ;;
  reset-full-demo) reset_full_demo ;;
  repair-db-permissions) repair_db_permissions ;;
  migrate-db) migrate_db ;;
  seed-smoke) seed_smoke ;;
  seed-demo) seed_demo ;;
  setup-backend) install_backend ;;
  setup-smcp) install_smcp ;;
  setup-aiagent) install_aiagent ;;
  setup-frontend) install_frontend ;;
  start-backend) start_backend ;;
  start-smcp) start_smcp ;;
  start-aiagent) start_aiagent ;;
  start-frontend) start_frontend ;;
  health) health ;;
  generate-snapshots) generate_snapshots ;;
  real-run) real_run ;;
  smoke) smoke ;;
  help|--help|-h) usage ;;
  *) usage; exit 1 ;;
esac
