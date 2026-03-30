import type { NextApiRequest, NextApiResponse } from 'next';
import { execSync } from 'child_process';
import { existsSync, readFileSync, readdirSync } from 'fs';
import path from 'path';
import { pool } from '@/lib/db';
import type { ArasSearchResponse, DocumentResult } from '@/lib/api';

/** Absolute path to the pipeline root (news_radar_mvp/). */
const PIPELINE_ROOT = path.resolve(
  process.cwd(), // newsradar_front/
  '..',           // news_radar_mvp/
);

/** Python executable inside the project venv. */
const PYTHON_BIN = path.join(PIPELINE_ROOT, '.venv', 'bin', 'python3');

const PIPELINE_TIMEOUT_MS = 300_000; // 5 minutes

/**
 * POST /api/aras/search
 *
 * Executes the real Python ARAS pipeline and returns classified results.
 * Falls back to PostgreSQL if the pipeline is unavailable.
 */
export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ArasSearchResponse | { error: string }>,
) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const {
    company,
    nit,
    risk_category,
    date_from,
    date_to,
    classifier = 'rules',
  } = req.body ?? {};

  // Validation
  if (!company && !nit) {
    return res.status(400).json({
      error: 'Se requiere company o nit para la búsqueda ARAS',
    });
  }
  if (!date_from || !date_to) {
    return res.status(400).json({
      error: 'Se requiere date_from y date_to (YYYY-MM-DD)',
    });
  }

  const runId = 'aras_' + Date.now();
  const outDir = path.join('out', runId);

  // Build CLI command
  const args: string[] = [
    PYTHON_BIN, '-m', 'extractor.main',
    '--adhoc',
    '--focus', 'aras_news',
    '--catalog', path.join(PIPELINE_ROOT, '..', 'catalog.yaml'),
    '--date-from', date_from,
    '--date-to', date_to,
    '--classifier', classifier === 'llm' ? 'llm' : 'rules',
    '--out', outDir,
  ];

  if (company) {
    args.push('--company', company);
  }
  if (nit) {
    args.push('--nit', nit);
  }

  const cmd = args
    .map((a) => (/\s/.test(a) ? `"${a.replace(/"/g, '\\"')}"` : a))
    .join(' ');

  try {
    // Execute the Python pipeline
    execSync(cmd, {
      cwd: PIPELINE_ROOT,
      timeout: PIPELINE_TIMEOUT_MS,
      stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env },
    });
  } catch (err: unknown) {
    const execErr = err as { status?: number; stderr?: Buffer; message?: string };

    // Check if Python is available at all
    if (execErr.message?.includes('ENOENT')) {
      return res.status(503).json({
        error: 'Python no está disponible en el servidor',
      });
    }

    const stderr = execErr.stderr?.toString().trim() ?? '';
    console.error('ARAS pipeline error:', stderr || execErr.message);

    return res.status(500).json({
      error: 'Error ejecutando pipeline ARAS: ' + (stderr.slice(-500) || 'unknown error'),
    });
  }

  // Read pipeline output
  const jsonlPath = path.join(PIPELINE_ROOT, outDir, 'articles.jsonl');

  if (!existsSync(jsonlPath)) {
    return res.status(200).json({
      run_id: runId,
      total_documents: 0,
      total_classified: 0,
      results: [],
      excel_url: null,
    });
  }

  const lines = readFileSync(jsonlPath, 'utf-8')
    .split('\n')
    .filter((l) => l.trim().length > 0);

  const results: DocumentResult[] = lines.map((line) => {
    const doc = JSON.parse(line);
    return {
      title: doc.title ?? '',
      source: doc.source_id ?? '',
      published_at: doc.published_at ?? null,
      url: doc.url ?? null,
      summary: doc.excerpt ?? '',
      category: doc.category ?? doc.risk_type ?? null,
      severity: doc.severity ?? null,
      evidence: (doc.evidence_spans ?? []).map(
        (s: { text: string }) => s.text,
      ),
    };
  });

  // Check for Excel file in output directory
  let excelUrl: string | null = null;
  const absOutDir = path.join(PIPELINE_ROOT, outDir);
  if (existsSync(absOutDir)) {
    const xlsxFiles = readdirSync(absOutDir).filter((f) =>
      f.endsWith('.xlsx'),
    );
    if (xlsxFiles.length > 0) {
      excelUrl = `/api/download/${runId}/${xlsxFiles[0]}`;
    }
  }

  // Store results in PostgreSQL (best-effort, don't fail the response)
  try {
    for (const line of lines) {
      const doc = JSON.parse(line);
      await pool.query(
        `INSERT INTO articles (title, source_id, published_at, url, summary, category, relevance_score, run_id)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
         ON CONFLICT DO NOTHING`,
        [
          doc.title,
          doc.source_id,
          doc.published_at ?? null,
          doc.url,
          doc.excerpt ?? '',
          doc.category ?? doc.risk_type ?? null,
          doc.relevance_score ?? null,
          runId,
        ],
      );
    }
  } catch (dbErr) {
    console.error('Failed to persist ARAS results to DB:', dbErr);
  }

  const response: ArasSearchResponse = {
    run_id: runId,
    total_documents: results.length,
    total_classified: results.filter((r) => r.category !== null).length,
    results,
    excel_url: excelUrl,
  };

  return res.status(200).json(response);
}
