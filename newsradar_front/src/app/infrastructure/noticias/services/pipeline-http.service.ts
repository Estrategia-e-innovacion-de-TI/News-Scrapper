import { Inject, Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { API_BASE_URL } from '../../../config/api.token';

export interface PipelineRunRequest {
  catalog_path?: string;
  days?: number;
  max_items_per_source?: number;
  focus?: string;
  adhoc?: boolean;
  company?: string;
  terms?: string;
  date_from?: string;
  date_to?: string;
  classifier_mode?: 'rules' | 'llm';
  dry_run?: boolean;
  nit?: string;
  terms_preset?: string;
}

export interface PipelineRunResponse {
  run_id: string;
  status: string;
}

export interface PipelineStatus {
  run_id: string;
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  total_sources: number;
  total_discovered: number;
  total_fetched: number;
  total_ok: number;
  total_errors: number;
  total_dupes: number;
}

export interface ExcelExportRequest {
  run_id: string;
  filters?: Record<string, unknown>;
}

export interface ExcelExportResponse {
  file_url: string;
  file_name: string;
  total_rows: number;
}

export interface SourceConfig {
  source_id: string;
  name: string;
  enabled: boolean;
  type: string;
  base_url: string;
  languages: string[];
  geo: string[];
}

export interface TrendmapGenerateResponse {
  snapshot_id: string;
}

@Injectable({ providedIn: 'root' })
export class PipelineHttpService {
  constructor(
    private http: HttpClient,
    @Inject(API_BASE_URL) private baseUrl: string,
  ) {}

  private handleError(error: HttpErrorResponse): Observable<never> {
    const message =
      error.status >= 500
        ? 'Error del servidor. Intente más tarde.'
        : (error.error?.detail ?? `Error: ${error.status}`);
    return throwError(() => new Error(message));
  }

  runPipeline(req: PipelineRunRequest): Observable<PipelineRunResponse> {
    return this.http
      .post<PipelineRunResponse>(`${this.baseUrl}/pipeline/run`, req)
      .pipe(catchError(this.handleError));
  }

  getPipelineStatus(runId: string): Observable<PipelineStatus> {
    return this.http
      .get<PipelineStatus>(`${this.baseUrl}/pipeline/status/${runId}`)
      .pipe(catchError(this.handleError));
  }

  exportExcel(req: ExcelExportRequest): Observable<ExcelExportResponse> {
    return this.http
      .post<ExcelExportResponse>(`${this.baseUrl}/export/excel`, req)
      .pipe(catchError(this.handleError));
  }

  getCatalogSources(focus?: string, enabled?: boolean): Observable<SourceConfig[]> {
    const params: Record<string, string> = {};
    if (focus) params['focus'] = focus;
    if (enabled !== undefined) params['enabled'] = String(enabled);
    return this.http
      .get<SourceConfig[]>(`${this.baseUrl}/catalog/sources`, { params })
      .pipe(catchError(this.handleError));
  }

  generateTrendmap(config?: Record<string, unknown>): Observable<TrendmapGenerateResponse> {
    return this.http
      .post<TrendmapGenerateResponse>(`${this.baseUrl}/trendmap/generate`, config ?? {})
      .pipe(catchError(this.handleError));
  }
}
