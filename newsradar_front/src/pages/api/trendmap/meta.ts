import type { NextApiRequest, NextApiResponse } from 'next';
import { pool } from '@/lib/db';
import type { TrendmapMetaResponse } from '@/lib/api';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<TrendmapMetaResponse | { error: string }>,
) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const [countsResult, dateRangeResult] = await Promise.all([
      pool.query(
        `SELECT
           COUNT(*) FILTER (WHERE source_type = 'news')  AS news,
           COUNT(*) FILTER (WHERE source_type = 'paper') AS papers,
           COUNT(*)                                       AS total
         FROM articles`,
      ),
      pool.query(
        `SELECT
           MIN(published_at) AS min_date,
           MAX(published_at) AS max_date
         FROM articles
         WHERE published_at IS NOT NULL`,
      ),
    ]);

    const counts = countsResult.rows[0];
    const dateRange = dateRangeResult.rows[0];

    const meta: TrendmapMetaResponse = {
      generated_at_utc: new Date().toISOString(),
      source_counts: {
        news: Number(counts.news),
        papers: Number(counts.papers),
        total: Number(counts.total),
      },
      date_range: {
        min: dateRange.min_date ? new Date(dateRange.min_date).toISOString() : '',
        max: dateRange.max_date ? new Date(dateRange.max_date).toISOString() : '',
      },
      methodology: {},
    };

    return res.status(200).json(meta);
  } catch (err) {
    console.error('Trendmap meta API error:', err);
    return res.status(503).json({ error: 'Base de datos no disponible' });
  }
}
