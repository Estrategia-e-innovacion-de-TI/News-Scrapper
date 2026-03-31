import { DocumentResult } from './document-result.model';

export interface ArasSearchRequest {
  company?: string;
  nit?: string;
  risk_category?: string;
  date_from?: string;
  date_to?: string;
  classifier?: 'rules' | 'llm';
}

export interface ArasSearchResponse {
  run_id: string;
  total_documents: number;
  total_classified: number;
  results: DocumentResult[];
  excel_url: string | null;
}
