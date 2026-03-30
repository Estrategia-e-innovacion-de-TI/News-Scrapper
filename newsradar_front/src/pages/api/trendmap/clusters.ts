import type { NextApiRequest, NextApiResponse } from 'next';
import { pool } from '@/lib/db';
import type { ClustersResponseFull, Cluster, SuperCluster, Article, TrendmapMeta } from '@/lib/api';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ClustersResponseFull | { error: string }>,
) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const [clustersResult, superClustersResult, articlesResult] = await Promise.all([
      pool.query(
        `SELECT cluster_id, label, category, summary, keywords, item_count,
                impact_score, horizon_score, avg_score, relevance,
                x_embed, y_embed, hull_polygon
         FROM clusters
         ORDER BY item_count DESC`,
      ),
      pool.query(
        `SELECT category, sub_cluster_ids, item_count, avg_score,
                x_embed, y_embed, hull_polygon
         FROM super_clusters
         ORDER BY category`,
      ),
      pool.query(
        `SELECT id::text, title, url, source_id, source_type, published_at,
                relevance_score, cluster_id, x_embed, y_embed, category, summary
         FROM articles
         ORDER BY relevance_score DESC`,
      ),
    ]);

    const clusters: Cluster[] = clustersResult.rows.map((r) => ({
      cluster_id: r.cluster_id,
      label: r.label,
      category: r.category ?? '',
      summary: r.summary ?? '',
      keywords: r.keywords ?? [],
      item_count: Number(r.item_count),
      impact_score: Number(r.impact_score),
      horizon_score: Number(r.horizon_score),
      avg_score: Number(r.avg_score),
      relevance: r.relevance ?? 'baja',
      x_embed: Number(r.x_embed),
      y_embed: Number(r.y_embed),
      hull_polygon: r.hull_polygon ?? [],
    }));

    const super_clusters: SuperCluster[] = superClustersResult.rows.map((r) => ({
      category: r.category,
      sub_cluster_ids: r.sub_cluster_ids ?? [],
      item_count: Number(r.item_count),
      avg_score: Number(r.avg_score),
      x_embed: Number(r.x_embed),
      y_embed: Number(r.y_embed),
      hull_polygon: r.hull_polygon ?? [],
    }));

    const articles: Article[] = articlesResult.rows.map((r) => ({
      id: r.id,
      title: r.title,
      url: r.url ?? null,
      source_id: r.source_id,
      source_type: r.source_type,
      published_at: r.published_at ? new Date(r.published_at).toISOString() : null,
      relevance_score: Number(r.relevance_score),
      cluster_id: r.cluster_id ?? '',
      x_embed: Number(r.x_embed),
      y_embed: Number(r.y_embed),
      category: r.category ?? null,
      summary: r.summary ?? null,
    }));

    // Build meta from aggregated article data
    const newsCount = articles.filter((a) => a.source_type === 'news').length;
    const papersCount = articles.filter((a) => a.source_type === 'paper').length;
    const dates = articles
      .map((a) => a.published_at)
      .filter((d): d is string => d !== null)
      .sort();

    const meta: TrendmapMeta = {
      generated_at_utc: new Date().toISOString(),
      source_counts: { news: newsCount, papers: papersCount, total: articles.length },
      date_range: {
        min: dates[0] ?? '',
        max: dates[dates.length - 1] ?? '',
      },
      methodology: {},
    };

    return res.status(200).json({ clusters, super_clusters, articles, meta });
  } catch (err) {
    console.error('Trendmap clusters API error:', err);
    return res.status(503).json({ error: 'Base de datos no disponible' });
  }
}
