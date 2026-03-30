import type { NextApiRequest, NextApiResponse } from 'next';
import { pool } from '@/lib/db';
import type { TrendsResponse, Trend } from '@/lib/api';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<TrendsResponse | { error: string }>,
) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { rows } = await pool.query(
      `SELECT trend, category, direction, momentum,
              maturity_stage, description, impact_on_finance
       FROM trends
       ORDER BY momentum DESC`,
    );

    const trends: Trend[] = rows.map((r) => ({
      trend: r.trend,
      category: r.category ?? '',
      direction: r.direction ?? 'estable',
      momentum: Number(r.momentum),
      maturity_stage: r.maturity_stage ?? 'trigger',
      description: r.description ?? '',
      impact_on_finance: r.impact_on_finance ?? '',
    }));

    return res.status(200).json({
      trends,
      clusters: [],
      key_insights: [],
      recommendations: [],
    });
  } catch (err) {
    console.error('Trendmap trends API error:', err);
    return res.status(503).json({ error: 'Base de datos no disponible' });
  }
}
