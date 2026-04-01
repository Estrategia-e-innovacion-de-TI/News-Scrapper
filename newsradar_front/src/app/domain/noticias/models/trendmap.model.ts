export type HypeStage =
  | 'innovation_trigger'
  | 'peak_of_inflated_expectations'
  | 'trough_of_disillusionment'
  | 'slope_of_enlightenment'
  | 'plateau_of_productivity';

export type LifecycleStage =
  | 'weak_signal'
  | 'innovation_trigger'
  | 'rising_attention'
  | 'peak_visibility'
  | 'correction'
  | 'consolidation'
  | 'productive_adoption';

export interface ScoreBreakdownComponent {
  name: string;
  weight: number;
  value: number;
  contribution: number;
}

export interface ScoreBreakdown {
  score: number;
  formula: string;
  components: ScoreBreakdownComponent[];
}

export interface TaxonomyMatch {
  name: string;
  score: number;
  matched_terms: string[];
  sector_tags?: string[];
  capability_tags?: string[];
}

export interface ClusterQuality {
  score: number;
  coherence: number;
  separation: number;
  taxonomy_focus: number;
  duplicate_pressure: number;
}

export interface InsightEvidence {
  type: string;
  detail: string;
}

export interface ComparativeClusterSignal {
  cluster_id: string;
  matched_previous_cluster: string | null;
  status: 'new' | 'accelerating' | 'cooling' | 'stable';
  delta_documents: number;
  delta_impact: number;
  delta_momentum: number;
  similarity: number;
}

export interface ComparativeSignals {
  previous_snapshot_available: boolean;
  summary: string;
  clusters: ComparativeClusterSignal[];
}

export interface QualityChecks {
  methodology_version: string;
  cluster_coherence_avg: number;
  cluster_quality_avg: number;
  unclustered_ratio: number;
  taxonomy_coverage: number;
  keyword_usefulness_ratio: number;
  weak_signal_clusters: number;
  low_quality_clusters: number;
}

export interface FiltersMetadata {
  categories: string[];
  source_types: string[];
  sources: string[];
  maturity_stages: HypeStage[];
  hype_stages: LifecycleStage[];
  recommended_sort_orders: string[];
  date_range?: {
    start: string | null;
    end: string | null;
  };
}

export interface ClusterCardSummary {
  cluster_id: string;
  label: string;
  subtitle: string;
  category: string;
  summary: string;
  impact_score: number;
  maturity_score: number;
  momentum_score: number;
  novelty_score: number;
  hype_stage: LifecycleStage;
  weak_signal_flag: boolean;
  item_count: number;
  quality_score: number;
  top_keywords: string[];
}

export interface TrendCardSummary {
  label: string;
  category: string;
  stage: LifecycleStage;
  impact_score: number;
  momentum_score: number;
  why_it_matters: string;
  decision_prompt: string;
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
  weak_signal_topics?: string[];
  source_diversity?: number;
  avg_relevance?: number;
  silhouette_score?: number;
  executive_summary?: string;
  cluster_quality_avg?: number;
  taxonomy_coverage?: number;
  methodology_version?: string;
}

export interface TrendmapMeta {
  generated_at: string;
  total_articles: number;
  total_papers: number;
  total_filtered: number;
  total_clusters: number;
  clustered_documents?: number;
  unclustered_documents?: number;
  total_categories: number;
  silhouette_score: number;
  methodology_version?: string;
}

export interface TrendmapArticle {
  id: string;
  title: string;
  source: string;
  source_type: 'news' | 'rss' | 'paper' | 'pdf' | 'institutional_report' | 'patent';
  date: string | null;
  score: number;
  url: string;
  x_embed: number;
  y_embed: number;
  cluster_id: string;
  cluster_label?: string;
  summary?: string;
  category?: string | null;
  risk_type?: string | null;
  dominant_risk?: string;
  taxonomy_matches?: TaxonomyMatch[];
  source_weight?: number;
  duplicate_signature?: string;
  duplicate_flag?: boolean;
  recency_score?: number;
  representative_reason?: string;
  cluster_quality_score?: number;
  hype_stage?: LifecycleStage;
  unclustered?: boolean;
}

export interface TrendmapCluster {
  cluster_id: string;
  label: string;
  subtitle: string;
  category: string;
  summary: string;
  rationale: string;
  keywords: string[];
  top_keywords: string[];
  relevance: 'alta' | 'media' | 'baja';
  item_count: number;
  documents?: number;
  effective_documents?: number;
  impact_score: number;
  avg_score: number;
  maturity_score: number;
  horizon_score: number;
  momentum_score: number;
  novelty_score: number;
  uncertainty_score: number;
  persistence_score?: number;
  risk_severity?: number | null;
  maturity_stage: HypeStage | string;
  hype_stage: LifecycleStage;
  weak_signal_flag: boolean;
  signal_state?: string;
  direction: 'up' | 'down' | 'stable' | string;
  growth_ratio: number;
  acceleration_ratio?: number;
  taxonomy_matches: TaxonomyMatch[];
  cluster_quality: ClusterQuality;
  maturity_score_breakdown: ScoreBreakdown;
  impact_score_breakdown: ScoreBreakdown;
  momentum_score_breakdown: ScoreBreakdown;
  novelty_score_breakdown: ScoreBreakdown;
  uncertainty_score_breakdown: ScoreBreakdown;
  risk_severity_breakdown?: ScoreBreakdown | null;
  hull_polygon: [number, number][];
  coords: { x: number; y: number };
  articles: string[];
  top_documents: TrendmapArticle[];
  representative_documents: TrendmapArticle[];
  source_mix: { source: string; count: number }[];
  insight_evidence: InsightEvidence[];
  executive_takeaway: string;
  what_is_happening: string;
  why_it_matters: string;
  decision_prompt: string;
  dominant_risk?: string | null;
  comparative_signal?: ComparativeClusterSignal;
}

export interface SuperCluster {
  category: string;
  clusters: string[];
  hull_polygon: [number, number][];
  total_items: number;
  avg_impact: number;
  avg_momentum?: number;
}

export interface TrendEntry {
  date: string;
  topic: string;
  risk?: string;
  cluster_id: string;
  count: number;
  avg_score: number;
  momentum_score?: number;
}

export interface RiskSignal {
  type: string;
  description: string;
  severity: 'H' | 'M' | 'L';
  related_clusters: string[];
}

export interface MethodologyBlock {
  methodology_version: string;
  representation?: Record<string, unknown>;
  clustering?: Record<string, unknown>;
  scoring?: Record<string, unknown>;
}

export interface TrendmapData {
  report_type: string;
  generated_at: string;
  window_months: number;
  version: number;
  methodology_version?: string;
  meta: TrendmapMeta;
  summary: TrendmapSummary;
  clusters: TrendmapCluster[];
  super_clusters: SuperCluster[];
  articles: TrendmapArticle[];
  documents?: TrendmapArticle[];
  trends: TrendEntry[];
  insights: string[];
  recommendations: string[];
  risk_signals: RiskSignal[];
  top_documents: TrendmapArticle[];
  cluster_cards?: ClusterCardSummary[];
  trend_cards?: TrendCardSummary[];
  taxonomy_breakdown?: { name: string; score: number }[];
  quality_checks?: QualityChecks;
  filters_metadata?: FiltersMetadata;
  weak_signals?: ClusterCardSummary[];
  comparative_signals?: ComparativeSignals;
  methodology?: MethodologyBlock;
  charts?: Record<string, unknown>;
  parameters?: Record<string, unknown>;
}

export const DARK_THEME = {
  bg: '#0f172a',
  surface: '#111827',
  border: '#243043',
  text: '#dbe4f0',
  textMuted: '#94a3b8',
  accent: '#f59e0b',
} as const;

export interface Cluster extends TrendmapCluster {}

export interface Trend {
  trend: string;
  category: string;
  direction: 'creciente' | 'decreciente' | 'estable';
  momentum: number;
  maturity_stage: HypeStage;
  description: string;
  impact_on_finance: string;
}
