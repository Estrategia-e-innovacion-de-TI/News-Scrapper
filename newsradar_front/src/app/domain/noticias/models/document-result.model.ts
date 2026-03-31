export interface DocumentResult {
  title: string;
  source: string;
  published_at: string | null;
  url: string | null;
  summary: string;
  category: string | null;
  severity: string | null;
  evidence: string[];
  confidence: number | null;
  matched_keywords: string[];
  events: string[];
  relevance_score: number | null;
}
