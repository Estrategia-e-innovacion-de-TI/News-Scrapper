import { InjectionToken } from '@angular/core';
import { Observable } from 'rxjs';
import type {
  ArasSearchRequest,
  ArasSearchResponse,
  RiesgosSearchRequest,
  RiesgosSearchResponse,
  TopicItem,
  SubscribeRequest,
  SubscribeResponse,
  Subscription,
  SubscriptionDelivery,
  Cluster,
  Trend,
} from '../../../domain/noticias/models';

export interface ClustersResponse {
  clusters: Cluster[];
}

export interface TrendsResponse {
  trends: Trend[];
}

export interface TrendmapMeta {
  last_updated: string;
  total_clusters: number;
  total_trends: number;
}

export interface RiesgosApiPort {
  searchAras(req: ArasSearchRequest): Observable<ArasSearchResponse>;
  searchRiesgos(req: RiesgosSearchRequest): Observable<RiesgosSearchResponse>;
}

export interface VigilanciaApiPort {
  fetchTopics(): Observable<TopicItem[]>;
  subscribe(req: SubscribeRequest): Observable<SubscribeResponse>;
  listSubscriptions(): Observable<Subscription[]>;
  listDeliveries(): Observable<SubscriptionDelivery[]>;
  deleteSubscription(id: string): Observable<void>;
}

export interface TrendmapApiPort {
  fetchClusters(): Observable<ClustersResponse>;
  fetchTrends(): Observable<TrendsResponse>;
  fetchMeta(): Observable<TrendmapMeta>;
}

export const RIESGOS_API = new InjectionToken<RiesgosApiPort>('RIESGOS_API');
export const VIGILANCIA_API = new InjectionToken<VigilanciaApiPort>('VIGILANCIA_API');
export const TRENDMAP_API = new InjectionToken<TrendmapApiPort>('TRENDMAP_API');
