/**
 * Seed script — loads JSON data from trendmap pipeline output into PostgreSQL.
 *
 * Usage:
 *   npx tsx scripts/seed.ts
 *   npx ts-node scripts/seed.ts
 *
 * Environment variables:
 *   TRENDMAP_JSON  — path to trendmap.json   (default: ../../trendmap/data/trendmap.json)
 *   LLM_JSON       — path to fresh_llm_analysis.json (default: ../../trendmap/data/fresh_llm_analysis.json)
 *   DATABASE_URL / PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD — PostgreSQL connection
 */

import * as fs from 'fs';
import * as path from 'path';
import { pool } from '../src/lib/db';

// ── JSON file paths (configurable via env) ───────────────────────────

const TRENDMAP_PATH = path.resolve(
  __dirname,
  process.env.TRENDMAP_JSON ?? '../../trendmap/data/trendmap.json',
);

const LLM_PATH = path.resolve(
  __dirname,
  process.env.LLM_JSON ?? '../../trendmap/data/fresh_llm_analysis.json',
);

// ── Type helpers for the raw JSON shapes ─────────────────────────────

interface RawArticle {
  article_id: string;
  cluster_id: string;
  title: string;
  excerpt?: string;
  url?: string;
  published_at?: string;
  relevance_score?: number;
  source_id: string;
  source_type: string;
  x_embed?: number;
  y_embed?: number;
}

interface RawCluster {
  cluster_id: string;
  label: string;
  category?: string;
  summary?: string;
  keywords?: string[];
  item_count?: number;
  impact_score?: number;
  horizon_score?: number;
  avg_score?: number;
  relevance?: string;
  x_embed?: number;
  y_embed?: number;
  hull_polygon?: number[][];
}

interface RawSuperCluster {
  category: string;
  sub_cluster_ids?: string[];
  item_count?: number;
  avg_score?: number;
  x_embed?: number;
  y_embed?: number;
  hull_polygon?: number[][];
}

interface RawTrend {
  trend: string;
  category?: string;
  direction?: string;
  momentum?: number;
  maturity_stage?: string;
  description?: string;
  impact_on_finance?: string;
}

interface TrendmapJSON {
  meta?: Record<string, unknown>;
  clusters?: RawCluster[];
  super_clusters?: RawSuperCluster[];
  articles?: RawArticle[];
  trends?: RawTrend[];
  insights?: string[];
  recommendations?: string[];
}

interface LLMAnalysisJSON {
  clusters?: { id: string; label: string; keywords?: string[]; summary?: string; relevance?: string }[];
  trends?: RawTrend[];
  key_insights?: string[];
  recommendations?: string[];
}

// ── Helpers ──────────────────────────────────────────────────────────

function readJSON<T>(filePath: string): T {
  const raw = fs.readFileSync(filePath, 'utf-8');
  return JSON.parse(raw) as T;
}

function log(msg: string) {
  console.log(`[seed] ${msg}`);
}

function logError(msg: string, err?: unknown) {
  console.error(`[seed] ERROR: ${msg}`, err instanceof Error ? err.message : err ?? '');
}

// ── Upsert functions ─────────────────────────────────────────────────

async function upsertArticles(articles: RawArticle[], runId: string): Promise<number> {
  // The articles table uses SERIAL id, so we deduplicate on (title, source_id).
  // We ensure idempotency by checking for existing rows before inserting.
  let count = 0;
  for (const a of articles) {
    const { rowCount } = await pool.query(
      `UPDATE articles SET
         url             = $3,
         source_type     = $4,
         published_at    = $5,
         relevance_score = $6,
         cluster_id      = $7,
         x_embed         = $8,
         y_embed         = $9,
         summary         = $10,
         run_id          = $11
       WHERE title = $1 AND source_id = $2`,
      [
        a.title,
        a.source_id,
        a.url ?? null,
        a.source_type,
        a.published_at ?? null,
        a.relevance_score ?? 0,
        a.cluster_id,
        a.x_embed ?? null,
        a.y_embed ?? null,
        a.excerpt ?? null,
        runId,
      ],
    );
    if ((rowCount ?? 0) === 0) {
      await pool.query(
        `INSERT INTO articles (title, url, source_id, source_type, published_at,
                               relevance_score, cluster_id, x_embed, y_embed, summary, run_id)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)`,
        [
          a.title,
          a.url ?? null,
          a.source_id,
          a.source_type,
          a.published_at ?? null,
          a.relevance_score ?? 0,
          a.cluster_id,
          a.x_embed ?? null,
          a.y_embed ?? null,
          a.excerpt ?? null,
          runId,
        ],
      );
    }
    count++;
  }
  return count;
}

async function upsertClusters(clusters: RawCluster[], runId: string): Promise<number> {
  let count = 0;
  for (const c of clusters) {
    await pool.query(
      `INSERT INTO clusters (cluster_id, label, category, summary, keywords, item_count,
                             impact_score, horizon_score, avg_score, relevance,
                             x_embed, y_embed, hull_polygon, run_id)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
       ON CONFLICT (cluster_id) DO UPDATE SET
         label         = EXCLUDED.label,
         category      = EXCLUDED.category,
         summary       = EXCLUDED.summary,
         keywords      = EXCLUDED.keywords,
         item_count    = EXCLUDED.item_count,
         impact_score  = EXCLUDED.impact_score,
         horizon_score = EXCLUDED.horizon_score,
         avg_score     = EXCLUDED.avg_score,
         relevance     = EXCLUDED.relevance,
         x_embed       = EXCLUDED.x_embed,
         y_embed       = EXCLUDED.y_embed,
         hull_polygon  = EXCLUDED.hull_polygon,
         run_id        = EXCLUDED.run_id`,
      [
        c.cluster_id,
        c.label,
        c.category ?? null,
        c.summary ?? null,
        JSON.stringify(c.keywords ?? []),
        c.item_count ?? 0,
        c.impact_score ?? 0,
        c.horizon_score ?? 0,
        c.avg_score ?? 0,
        c.relevance ?? null,
        c.x_embed ?? null,
        c.y_embed ?? null,
        JSON.stringify(c.hull_polygon ?? []),
        runId,
      ],
    );
    count++;
  }
  return count;
}

async function upsertSuperClusters(superClusters: RawSuperCluster[], runId: string): Promise<number> {
  let count = 0;
  for (const sc of superClusters) {
    await pool.query(
      `INSERT INTO super_clusters (category, sub_cluster_ids, item_count, avg_score,
                                   x_embed, y_embed, hull_polygon, run_id)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
       ON CONFLICT (category) DO UPDATE SET
         sub_cluster_ids = EXCLUDED.sub_cluster_ids,
         item_count      = EXCLUDED.item_count,
         avg_score       = EXCLUDED.avg_score,
         x_embed         = EXCLUDED.x_embed,
         y_embed         = EXCLUDED.y_embed,
         hull_polygon    = EXCLUDED.hull_polygon,
         run_id          = EXCLUDED.run_id`,
      [
        sc.category,
        JSON.stringify(sc.sub_cluster_ids ?? []),
        sc.item_count ?? 0,
        sc.avg_score ?? 0,
        sc.x_embed ?? null,
        sc.y_embed ?? null,
        JSON.stringify(sc.hull_polygon ?? []),
        runId,
      ],
    );
    count++;
  }
  return count;
}

async function upsertTrends(trends: RawTrend[], runId: string): Promise<number> {
  let count = 0;
  for (const t of trends) {
    // Use (trend, category) as a logical unique key via ON CONFLICT DO NOTHING
    // Since the trends table has no unique constraint on (trend, category),
    // we first try to update existing rows, then insert if none matched.
    const { rowCount } = await pool.query(
      `UPDATE trends SET
         direction         = $3,
         momentum          = $4,
         maturity_stage    = $5,
         description       = $6,
         impact_on_finance = $7,
         run_id            = $8
       WHERE trend = $1 AND (category = $2 OR (category IS NULL AND $2 IS NULL))`,
      [
        t.trend,
        t.category ?? null,
        t.direction ?? null,
        t.momentum ?? 0,
        t.maturity_stage ?? null,
        t.description ?? null,
        t.impact_on_finance ?? null,
        runId,
      ],
    );
    if ((rowCount ?? 0) === 0) {
      await pool.query(
        `INSERT INTO trends (trend, category, direction, momentum, maturity_stage,
                             description, impact_on_finance, run_id)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
        [
          t.trend,
          t.category ?? null,
          t.direction ?? null,
          t.momentum ?? 0,
          t.maturity_stage ?? null,
          t.description ?? null,
          t.impact_on_finance ?? null,
          runId,
        ],
      );
    }
    count++;
  }
  return count;
}

// ── Update article categories from cluster data ──────────────────────

async function updateArticleCategories(clusters: RawCluster[]): Promise<void> {
  for (const c of clusters) {
    if (c.category) {
      await pool.query(
        `UPDATE articles SET category = $1 WHERE cluster_id = $2 AND (category IS NULL OR category != $1)`,
        [c.category, c.cluster_id],
      );
    }
  }
}

// ── Main ─────────────────────────────────────────────────────────────

async function main() {
  const runId = `seed_${new Date().toISOString().replace(/[:.]/g, '-')}`;
  log(`Starting seed (run_id: ${runId})`);

  // ── 1. Load trendmap.json ──────────────────────────────────────────
  log(`Reading trendmap data from: ${TRENDMAP_PATH}`);
  let trendmap: TrendmapJSON;
  try {
    trendmap = readJSON<TrendmapJSON>(TRENDMAP_PATH);
  } catch (err) {
    logError(`Failed to read trendmap.json at ${TRENDMAP_PATH}`, err);
    process.exit(1);
  }

  // ── 2. Load fresh_llm_analysis.json ────────────────────────────────
  log(`Reading LLM analysis from: ${LLM_PATH}`);
  let llm: LLMAnalysisJSON;
  try {
    llm = readJSON<LLMAnalysisJSON>(LLM_PATH);
  } catch (err) {
    logError(`Failed to read fresh_llm_analysis.json at ${LLM_PATH}`, err);
    process.exit(1);
  }

  // ── 3. Seed clusters ──────────────────────────────────────────────
  const clusters = trendmap.clusters ?? [];
  log(`Upserting ${clusters.length} clusters…`);
  try {
    const n = await upsertClusters(clusters, runId);
    log(`  ✓ ${n} clusters upserted`);
  } catch (err) {
    logError('Failed to upsert clusters', err);
    process.exit(1);
  }

  // ── 4. Seed super_clusters ────────────────────────────────────────
  const superClusters = trendmap.super_clusters ?? [];
  log(`Upserting ${superClusters.length} super_clusters…`);
  try {
    const n = await upsertSuperClusters(superClusters, runId);
    log(`  ✓ ${n} super_clusters upserted`);
  } catch (err) {
    logError('Failed to upsert super_clusters', err);
    process.exit(1);
  }

  // ── 5. Seed articles ──────────────────────────────────────────────
  const articles = trendmap.articles ?? [];
  log(`Upserting ${articles.length} articles…`);
  try {
    const n = await upsertArticles(articles, runId);
    log(`  ✓ ${n} articles upserted`);
  } catch (err) {
    logError('Failed to upsert articles', err);
    process.exit(1);
  }

  // ── 6. Update article categories from cluster data ────────────────
  log('Updating article categories from cluster data…');
  try {
    await updateArticleCategories(clusters);
    log('  ✓ Article categories updated');
  } catch (err) {
    logError('Failed to update article categories', err);
    // Non-fatal — continue
  }

  // ── 7. Seed trends from trendmap.json ─────────────────────────────
  const trendmapTrends = trendmap.trends ?? [];
  log(`Upserting ${trendmapTrends.length} trends from trendmap.json…`);
  try {
    const n = await upsertTrends(trendmapTrends, runId);
    log(`  ✓ ${n} trends upserted`);
  } catch (err) {
    logError('Failed to upsert trendmap trends', err);
    process.exit(1);
  }

  // ── 8. Seed trends from fresh_llm_analysis.json ───────────────────
  const llmTrends = llm.trends ?? [];
  log(`Upserting ${llmTrends.length} trends from fresh_llm_analysis.json…`);
  try {
    const n = await upsertTrends(llmTrends, runId);
    log(`  ✓ ${n} LLM trends upserted`);
  } catch (err) {
    logError('Failed to upsert LLM trends', err);
    process.exit(1);
  }

  // ── Done ──────────────────────────────────────────────────────────
  log('Seed completed successfully.');
}

main()
  .catch((err) => {
    logError('Unexpected error during seed', err);
    process.exit(1);
  })
  .finally(() => {
    pool.end().catch(() => {});
  });
