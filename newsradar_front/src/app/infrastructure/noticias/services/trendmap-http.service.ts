import { Inject, Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { API_BASE_URL } from '../../../config/api.token';
import {
  TrendmapApiPort,
  ClustersResponse,
  TrendsResponse,
  TrendmapMeta,
} from './noticias-api.token';
import { TrendmapData } from '../../../domain/noticias/models';

@Injectable()
export class TrendmapHttpService implements TrendmapApiPort {
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

  /** Fetch full TrendmapResponse from GET /api/trendmap/ */
  fetchFullTrendmap(): Observable<TrendmapData> {
    return this.http
      .get<TrendmapData>(`${this.baseUrl}/trendmap/`)
      .pipe(catchError(this.handleError));
  }

  fetchClusters(): Observable<ClustersResponse> {
    return this.http
      .get<ClustersResponse>(`${this.baseUrl}/trendmap/clusters`)
      .pipe(catchError(this.handleError));
  }

  fetchTrends(): Observable<TrendsResponse> {
    return this.http
      .get<TrendsResponse>(`${this.baseUrl}/trendmap/trends`)
      .pipe(catchError(this.handleError));
  }

  fetchMeta(): Observable<TrendmapMeta> {
    return this.http
      .get<TrendmapMeta>(`${this.baseUrl}/trendmap/meta`)
      .pipe(catchError(this.handleError));
  }
}
