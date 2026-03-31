import { Inject, Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { API_BASE_URL } from '../../../config/api.token';
import {
  TopicItem,
  SubscribeRequest,
  SubscribeResponse,
  Subscription,
  SubscriptionDelivery,
} from '../../../domain/noticias/models';
import { VigilanciaApiPort } from './noticias-api.token';

@Injectable()
export class VigilanciaHttpService implements VigilanciaApiPort {
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

  fetchTopics(): Observable<TopicItem[]> {
    return this.http
      .get<TopicItem[]>(`${this.baseUrl}/vigilancia/topics`)
      .pipe(catchError(this.handleError));
  }

  subscribe(req: SubscribeRequest): Observable<SubscribeResponse> {
    return this.http
      .post<SubscribeResponse>(`${this.baseUrl}/vigilancia/subscribe`, req)
      .pipe(catchError(this.handleError));
  }

  listSubscriptions(): Observable<Subscription[]> {
    return this.http
      .get<Subscription[]>(`${this.baseUrl}/subscriptions/`)
      .pipe(catchError(this.handleError));
  }

  listDeliveries(): Observable<SubscriptionDelivery[]> {
    return this.http
      .get<SubscriptionDelivery[]>(`${this.baseUrl}/subscriptions/deliveries`)
      .pipe(catchError(this.handleError));
  }

  deleteSubscription(id: string): Observable<void> {
    return this.http
      .delete<void>(`${this.baseUrl}/subscriptions/${id}`)
      .pipe(catchError(this.handleError));
  }
}
