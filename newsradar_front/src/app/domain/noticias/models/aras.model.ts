import { DocumentResult } from './document-result.model';

export interface ArasSearchRequest {
  company?: string;
  issuer?: string;
  nit?: string;
  term?: string;
  terms?: string[];
  risk_category?: string;
  date_from?: string;
  date_to?: string;
  classifier?: 'rules' | 'llm';
}

export interface ArasSearchResponse {
  run_id: string;
  search_id?: string | null;
  audit_id?: string | null;
  export_id?: string | null;
  total_documents: number;
  total_classified: number;
  results: DocumentResult[];
  excel_url: string | null;
}
