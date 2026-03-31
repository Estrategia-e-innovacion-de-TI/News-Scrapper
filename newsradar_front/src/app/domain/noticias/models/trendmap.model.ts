export type HypeStage =
  | 'trigger'
  | 'peak_of_inflated_expectations'
  | 'trough_of_disillusionment'
  | 'slope_of_enlightenment'
  | 'plateau_of_productivity';

export interface TrendmapData {
  meta: TrendmapMeta;
  summary?: TrendmapSummary;
  clusters: TrendmapCluster[];
  super_clusters: SuperCluster[];
  articles: TrendmapArticle[];
  trends: TrendEntry[];
  insights: string[];
  recommendations: string[];
  risk_signals: RiskSignal[];
}

export interface TrendmapSummary {
  total_documents: number;
  total_clusters: number;
  clustered_documents?: number;
  unclustered_documents?: number;
  dominant_topics?: string[];
  dominant_risks?: string[];
  emerging_topics?: string[];
  consolidating_topics?: string[];
  source_diversity?: number;
  avg_relevance?: number;
  silhouette_score?: number;
  executive_summary?: string;
}

export interface TrendmapMeta {
  generated_at: string;
  total_articles: number;
  total_papers: number;
  total_filtered: number;
  total_clusters: number;
  total_categories: number;
  silhouette_score: number;
}

export interface TrendmapCluster {
  cluster_id: string;
  label: string;
  category: string;
  summary: string;
  keywords: string[];
  relevance: 'alta' | 'media' | 'baja';
  item_count: number;
  impact_score: number;
  horizon_score: number;
  maturity_stage: string;
  hull_polygon: [number, number][];
  articles: string[];
}

export interface TrendmapArticle {
  id: string;
  title: string;
  source: string;
  source_type: 'news' | 'paper';
  date: string;
  score: number;
  url: string;
  x_embed: number;
  y_embed: number;
  cluster_id: string;
}

export interface SuperCluster {
  category: string;
  clusters: string[];
  hull_polygon: [number, number][];
  total_items: number;
  avg_impact: number;
}

export interface TrendEntry {
  date: string;
  topic: string;
  count: number;
  avg_score: number;
}

export interface RiskSignal {
  type: string;
  description: string;
  severity: 'H' | 'M' | 'L';
  related_clusters: string[];
}

export const DARK_THEME = {
  bg: '#0d1117',
  surface: '#161b22',
  border: '#21262d',
  text: '#c9d1d9',
  textMuted: '#8b949e',
  accent: '#58a6ff',
} as const;

/**
 * Legacy interfaces kept for backward compatibility with existing components.
 * New code should use TrendmapCluster instead of Cluster.
 */
export interface Cluster {
  cluster_id: string;
  label: string;
  category: string;
  summary: string;
  keywords: string[];
  item_count: number;
  impact_score: number;
  horizon_score: number;
  hull_polygon: number[][];
  avg_score: number;
  x_embed: number;
  y_embed: number;
  relevance: 'alta' | 'media' | 'baja';
  maturity_stage: string;
  articles: string[];
}

export interface Trend {
  trend: string;
  category: string;
  direction: 'creciente' | 'decreciente' | 'estable';
  momentum: number;
  maturity_stage: HypeStage;
  description: string;
  impact_on_finance: string;
}
