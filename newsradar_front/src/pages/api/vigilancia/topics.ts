import type { NextApiRequest, NextApiResponse } from 'next';
import type { TopicsResponse, TopicItem } from '@/lib/api';

/**
 * Static list of vigilancia topic groups, matching the mock backend.
 * Since there is no dedicated topics table in PostgreSQL, we serve a
 * hardcoded list derived from the categories used in the clusters table.
 */
const TOPICS: TopicItem[] = [
  { group_id: 'ia_ml', display_name: 'Inteligencia Artificial y Machine Learning', term_count: 24 },
  { group_id: 'blockchain', display_name: 'Blockchain y Criptoactivos', term_count: 18 },
  { group_id: 'ciberseguridad', display_name: 'Ciberseguridad', term_count: 32 },
  { group_id: 'fintech', display_name: 'Fintech e Innovación Financiera', term_count: 21 },
  { group_id: 'regtech', display_name: 'RegTech y Cumplimiento Regulatorio', term_count: 15 },
  { group_id: 'cloud', display_name: 'Cloud Computing e Infraestructura', term_count: 19 },
  { group_id: 'datos', display_name: 'Ciencia de Datos y Analítica', term_count: 22 },
  { group_id: 'banca_digital', display_name: 'Banca Digital y Pagos', term_count: 17 },
];

/**
 * GET /api/vigilancia/topics
 *
 * Returns the list of available vigilancia topic groups.
 */
export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<TopicsResponse | { error: string }>,
) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    return res.status(200).json({ topics: TOPICS });
  } catch (err) {
    console.error('Vigilancia topics API error:', err);
    return res.status(503).json({ error: 'Base de datos no disponible' });
  }
}
