import type { NextApiRequest, NextApiResponse } from 'next';
import { pool } from '@/lib/db';
import type { PipelineRun } from '@/lib/api';

const VALID_RUN_TYPES = ['trendmap', 'aras', 'riesgos', 'vigilancia'] as const;

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<PipelineRun | { error: string }>,
) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { run_type } = req.body ?? {};

  if (!run_type || !VALID_RUN_TYPES.includes(run_type)) {
    return res.status(400).json({
      error: `Invalid run_type. Must be one of: ${VALID_RUN_TYPES.join(', ')}`,
    });
  }

  try {
    // Insert a new pipeline_runs record with status "pending"
    const insertResult = await pool.query(
      `INSERT INTO pipeline_runs (run_type, status, started_at, config)
       VALUES ($1, 'pending', NOW(), '{}')
       RETURNING id, run_type, status, started_at, completed_at, config, result_summary, error_message`,
      [run_type],
    );

    const row = insertResult.rows[0];

    // Placeholder: mark as completed immediately
    // In a real implementation this would spawn the pipeline process asynchronously
    const updateResult = await pool.query(
      `UPDATE pipeline_runs
       SET status = 'completed', completed_at = NOW(), result_summary = $2
       WHERE id = $1
       RETURNING id, run_type, status, started_at, completed_at, config, result_summary, error_message`,
      [row.id, JSON.stringify({ message: `Pipeline ${run_type} completed (placeholder)` })],
    );

    const updated = updateResult.rows[0];

    const pipelineRun: PipelineRun = {
      id: updated.id,
      run_type: updated.run_type,
      status: updated.status,
      started_at: new Date(updated.started_at).toISOString(),
      completed_at: updated.completed_at ? new Date(updated.completed_at).toISOString() : null,
      config: updated.config ?? {},
      result_summary: updated.result_summary ?? null,
      error_message: updated.error_message ?? null,
    };

    return res.status(201).json(pipelineRun);
  } catch (err) {
    console.error('Pipeline run API error:', err);
    return res.status(503).json({ error: 'Base de datos no disponible' });
  }
}
