import type { NextApiRequest, NextApiResponse } from 'next';
import { pool } from '@/lib/db';
import type { SubscribeResponse } from '@/lib/api';

/**
 * POST /api/vigilancia/subscribe
 *
 * Inserts a subscription into the `subscriptions` table.
 * Expects JSON body: { email: string, name: string, query_groups: string[] }
 */
export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<SubscribeResponse | { error: string }>,
) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { email, name, query_groups } = req.body ?? {};

  // Validate email format
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!email || !emailRegex.test(email)) {
    return res.status(400).json({ error: 'Invalid email format' });
  }

  // Validate name
  if (!name || String(name).trim() === '') {
    return res.status(400).json({ error: 'Name is required' });
  }

  // Validate query_groups
  if (!query_groups || !Array.isArray(query_groups) || query_groups.length === 0) {
    return res.status(400).json({ error: 'At least one topic is required' });
  }

  try {
    await pool.query(
      `INSERT INTO subscriptions (email, name, query_groups)
       VALUES ($1, $2, $3)`,
      [email, String(name).trim(), JSON.stringify(query_groups)],
    );

    const response: SubscribeResponse = {
      status: 'ok',
      email,
      subscribed_groups: query_groups,
    };

    return res.status(200).json(response);
  } catch (err) {
    console.error('Vigilancia subscribe API error:', err);
    return res.status(503).json({ error: 'Base de datos no disponible' });
  }
}
