import { Inject, Injectable, computed, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { API_BASE_URL } from '../../../config/api.token';
import {
  TrendmapData,
  TrendmapCluster,
  TrendmapArticle,
} from '../../../domain/noticias/models';

@Injectable({ providedIn: 'root' })
export class TrendmapSignalService {
  /** Raw trendmap payload from the API */
  readonly data = signal<TrendmapData | null>(null);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  /** UI state */
  readonly selectedCluster = signal<TrendmapCluster | null>(null);
  readonly filterCategory = signal<string | null>(null);
  readonly filterSourceType = signal<'news' | 'paper' | null>(null);

  /** Filtered clusters: by category */
  readonly filteredClusters = computed(() => {
    const d = this.data();
    if (!d) return [];
    const cat = this.filterCategory();
    return cat ? d.clusters.filter((c) => c.category === cat) : d.clusters;
  });

  /** Filtered articles: by source type and by category (through cluster membership) */
  readonly filteredArticles = computed(() => {
    const d = this.data();
    if (!d) return [];

    let articles = d.articles;

    const sourceType = this.filterSourceType();
    if (sourceType) {
      articles = articles.filter((a) => a.source_type === sourceType);
    }

    const cat = this.filterCategory();
    if (cat) {
      const clusterIds = new Set(
        d.clusters.filter((c) => c.category === cat).map((c) => c.cluster_id),
      );
      articles = articles.filter((a) => clusterIds.has(a.cluster_id));
    }

    return articles;
  });

  /** Articles belonging to the currently selected cluster */
  readonly selectedClusterArticles = computed(() => {
    const cluster = this.selectedCluster();
    const d = this.data();
    if (!cluster || !d) return [];
    const ids = new Set(cluster.articles);
    return d.articles.filter((a) => ids.has(a.id));
  });

  /** Unique categories derived from clusters */
  readonly categories = computed(() => {
    const d = this.data();
    if (!d) return [];
    return [...new Set(d.clusters.map((c) => c.category))];
  });

  constructor(
    private http: HttpClient,
    @Inject(API_BASE_URL) private baseUrl: string,
  ) {}

  /** Fetch full trendmap data from GET /api/trendmap/ */
  load(): void {
    this.loading.set(true);
    this.error.set(null);

    this.http.get<TrendmapData>(`${this.baseUrl}/trendmap/`).subscribe({
      next: (response) => {
        this.data.set(response);
        this.loading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        const message =
          err.status >= 500
            ? 'Error del servidor. Intente más tarde.'
            : (err.error?.detail ?? `Error: ${err.status}`);
        this.error.set(message);
        this.loading.set(false);
      },
    });
  }

  selectCluster(cluster: TrendmapCluster | null): void {
    this.selectedCluster.set(cluster);
  }

  setFilterCategory(category: string | null): void {
    this.filterCategory.set(category);
  }

  setFilterSourceType(sourceType: 'news' | 'paper' | null): void {
    this.filterSourceType.set(sourceType);
  }

  clearFilters(): void {
    this.filterCategory.set(null);
    this.filterSourceType.set(null);
    this.selectedCluster.set(null);
  }
}
