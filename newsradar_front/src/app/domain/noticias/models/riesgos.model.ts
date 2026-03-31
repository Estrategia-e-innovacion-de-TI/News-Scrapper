import { DocumentResult } from './document-result.model';

export type RiesgosPreset = 'ciber' | 'fraude' | 'operacional' | 'ambiental_social' | 'all';

export interface RiesgosSearchRequest {
  terms?: string[];
  terms_preset?: RiesgosPreset;
  date_from?: string;
  date_to?: string;
  classifier?: 'rules' | 'llm';
}

export interface RiesgosSearchResponse {
  run_id: string;
  search_id?: string | null;
  audit_id?: string | null;
  export_id?: string | null;
  total_documents: number;
  total_classified: number;
  results: DocumentResult[];
  excel_url: string | null;
}
