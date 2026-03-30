-- NewsRadar Frontend Evolution — PostgreSQL Schema Migration
-- Idempotent: safe to run multiple times (IF NOT EXISTS on all objects)

-- ============================================================
-- Tables
-- ============================================================

CREATE TABLE IF NOT EXISTS articles (
  id            SERIAL PRIMARY KEY,
  title         TEXT NOT NULL,
  url           TEXT,
  source_id     TEXT NOT NULL,
  source_type   TEXT NOT NULL CHECK (source_type IN ('news', 'paper')),
  published_at  TIMESTAMPTZ,
  relevance_score NUMERIC(5,2) DEFAULT 0,
  cluster_id    TEXT,
  x_embed       DOUBLE PRECISION,
  y_embed       DOUBLE PRECISION,
  category      TEXT,
  summary       TEXT,
  run_id        TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS clusters (
  cluster_id    TEXT PRIMARY KEY,
  label         TEXT NOT NULL,
  category      TEXT,
  summary       TEXT,
  keywords      JSONB DEFAULT '[]',
  item_count    INTEGER DEFAULT 0,
  impact_score  NUMERIC(5,2) DEFAULT 0,
  horizon_score NUMERIC(5,4) DEFAULT 0,
  avg_score     NUMERIC(5,2) DEFAULT 0,
  relevance     TEXT CHECK (relevance IN ('alta', 'media', 'baja')),
  x_embed       DOUBLE PRECISION,
  y_embed       DOUBLE PRECISION,
  hull_polygon  JSONB DEFAULT '[]',
  run_id        TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS super_clusters (
  category      TEXT PRIMARY KEY,
  sub_cluster_ids JSONB DEFAULT '[]',
  item_count    INTEGER DEFAULT 0,
  avg_score     NUMERIC(5,2) DEFAULT 0,
  x_embed       DOUBLE PRECISION,
  y_embed       DOUBLE PRECISION,
  hull_polygon  JSONB DEFAULT '[]',
  run_id        TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trends (
  id            SERIAL PRIMARY KEY,
  trend         TEXT NOT NULL,
  category      TEXT,
  direction     TEXT CHECK (direction IN ('creciente', 'decreciente', 'estable')),
  momentum      NUMERIC(5,4) DEFAULT 0,
  maturity_stage TEXT,
  description   TEXT,
  impact_on_finance TEXT,
  run_id        TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS subscriptions (
  id            SERIAL PRIMARY KEY,
  email         TEXT NOT NULL,
  name          TEXT NOT NULL,
  query_groups  JSONB DEFAULT '[]',
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
  id            TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
  run_type      TEXT NOT NULL CHECK (run_type IN ('trendmap', 'aras', 'riesgos', 'vigilancia')),
  status        TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
  started_at    TIMESTAMPTZ DEFAULT NOW(),
  completed_at  TIMESTAMPTZ,
  config        JSONB DEFAULT '{}',
  result_summary JSONB,
  error_message TEXT
);

-- ============================================================
-- Indices
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_articles_cluster ON articles(cluster_id);
CREATE INDEX IF NOT EXISTS idx_articles_source_type ON articles(source_type);
CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at);
CREATE INDEX IF NOT EXISTS idx_clusters_category ON clusters(category);
CREATE INDEX IF NOT EXISTS idx_trends_category ON trends(category);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_type ON pipeline_runs(run_type);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status);
