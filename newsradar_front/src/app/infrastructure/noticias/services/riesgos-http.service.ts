import { Inject, Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { API_BASE_URL } from '../../../config/api.token';
import {
  ArasSearchRequest,
  ArasSearchResponse,
  RiesgosSearchRequest,
  RiesgosSearchResponse,
} from '../../../domain/noticias/models';
import { RiesgosApiPort } from './noticias-api.token';

@Injectable()
export class RiesgosHttpService implements RiesgosApiPort {
  constructor(
    private http: HttpClient,
    @Inject(API_BASE_URL) private baseUrl: string,
  ) {}

  searchAras(req: ArasSearchRequest): Observable<ArasSearchResponse> {
    return this.http
      .post<ArasSearchResponse>(`${this.baseUrl}/aras/search`, req)
      .pipe(
        catchError((error: HttpErrorResponse) => {
          const message =
            error.status >= 500
              ? 'Error del servidor. Intente más tarde.'
              : (error.error?.detail ?? `Error: ${error.status}`);
          return throwError(() => new Error(message));
        }),
      );
  }

  searchRiesgos(req: RiesgosSearchRequest): Observable<RiesgosSearchResponse> {
    return this.http
      .post<RiesgosSearchResponse>(`${this.baseUrl}/riesgos/search`, req)
      .pipe(
        catchError((error: HttpErrorResponse) => {
          const message =
            error.status >= 500
              ? 'Error del servidor. Intente más tarde.'
              : (error.error?.detail ?? `Error: ${error.status}`);
          return throwError(() => new Error(message));
        }),
      );
  }
}
