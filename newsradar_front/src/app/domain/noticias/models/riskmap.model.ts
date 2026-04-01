import {
  ClusterCardSummary,
  ComparativeSignals,
  FiltersMetadata,
  MethodologyBlock,
  QualityChecks,
  RiskSignal,
  SuperCluster,
  TaxonomyMatch,
  TrendCardSummary,
  TrendEntry,
  TrendmapArticle,
  TrendmapCluster,
  TrendmapMeta,
  TrendmapSummary,
} from './trendmap.model';

export interface RiskmapCluster extends TrendmapCluster {
  dominant_risk: string;
  risk_severity: number;
  persistence_score: number;
}

export interface RiskmapData {
  report_type: string;
  generated_at: string;
  window_months: number;
  version: number;
  methodology_version?: string;
  meta: TrendmapMeta;
  summary: TrendmapSummary;
  clusters: RiskmapCluster[];
  super_clusters: SuperCluster[];
  documents: TrendmapArticle[];
  articles: TrendmapArticle[];
  charts?: Record<string, unknown>;
  timeline?: TrendEntry[];
  top_documents: TrendmapArticle[];
  insights: string[];
  recommendations: string[];
  risk_signals: RiskSignal[];
  cluster_cards?: ClusterCardSummary[];
  trend_cards?: TrendCardSummary[];
  taxonomy_breakdown?: { name: string; score: number }[];
  quality_checks?: QualityChecks;
  filters_metadata?: FiltersMetadata;
  weak_signals?: ClusterCardSummary[];
  comparative_signals?: ComparativeSignals;
  methodology?: MethodologyBlock;
  parameters?: Record<string, unknown>;
}

export type { TaxonomyMatch };
