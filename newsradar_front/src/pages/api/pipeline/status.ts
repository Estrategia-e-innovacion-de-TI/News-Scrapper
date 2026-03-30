import type { NextApiRequest, NextApiResponse } from 'next';
import { pool } from '@/lib/db';
import type { PipelineRun } from '@/lib/api';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<PipelineRun[] | { error: string }>,
) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const result = await pool.query(
      `SELECT id, run_type, status, started_at, completed_at, config, result_summary, error_message
       FROM pipeline_runs
       ORDER BY started_at DESC
       LIMIT 20`,
    );

    const runs: PipelineRun[] = result.rows.map((r) => ({
      id: r.id,
      run_type: r.run_type,
      status: r.status,
      started_at: new Date(r.started_at).toISOString(),
      completed_at: r.completed_at ? new Date(r.completed_at).toISOString() : null,
      config: r.config ?? {},
      result_summary: r.result_summary ?? null,
      error_message: r.error_message ?? null,
    }));

    return res.status(200).json(runs);
  } catch (err) {
    console.error('Pipeline status API error:', err);
    return res.status(503).json({ error: 'Base de datos no disponible' });
  }
}
