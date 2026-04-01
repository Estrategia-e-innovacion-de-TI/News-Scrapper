import { Inject, Injectable, computed, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { API_BASE_URL } from '../../../config/api.token';
import {
  LifecycleStage,
  TrendmapArticle,
  TrendmapCluster,
  TrendmapData,
} from '../../../domain/noticias/models';

export type ClusterSort =
  | 'impact'
  | 'momentum'
  | 'novelty'
  | 'size'
  | 'quality'
  | 'maturity';

@Injectable({ providedIn: 'root' })
export class TrendmapSignalService {
  readonly data = signal<TrendmapData | null>(null);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  readonly selectedCluster = signal<TrendmapCluster | null>(null);
  readonly filterCategory = signal<string | null>(null);
  readonly filterSourceType = signal<string | null>(null);
  readonly filterMaturityStage = signal<string | null>(null);
  readonly filterHypeStage = signal<LifecycleStage | null>(null);
  readonly filterSignalState = signal<string | null>(null);
  readonly filterComparativeStatus = signal<'new' | 'accelerating' | 'cooling' | 'stable' | null>(null);
  readonly filterNoveltyBand = signal<string | null>(null);
  readonly weakSignalsOnly = signal(false);
  readonly sortBy = signal<ClusterSort>('impact');

  readonly categories = computed(() => {
    const d = this.data();
    if (!d) return [];
    return d.filters_metadata?.categories ?? [...new Set(d.clusters.map((cluster) => cluster.category))];
  });

  readonly filteredClusters = computed(() => {
    const d = this.data();
    if (!d) return [];

    const category = this.filterCategory();
    const maturityStage = this.filterMaturityStage();
    const hypeStage = this.filterHypeStage();
    const signalState = this.filterSignalState();
    const comparativeStatus = this.filterComparativeStatus();
    const noveltyBand = this.filterNoveltyBand();
    const weakOnly = this.weakSignalsOnly();
    const sortBy = this.sortBy();

    const clusters = d.clusters.filter((cluster) => {
      if (category && cluster.category !== category) return false;
      if (maturityStage && cluster.maturity_stage !== maturityStage) return false;
      if (hypeStage && cluster.hype_stage !== hypeStage) return false;
      if (signalState && cluster.signal_state !== signalState) return false;
      if (comparativeStatus && cluster.comparative_signal?.status !== comparativeStatus) return false;
      if (noveltyBand && cluster.novelty_band !== noveltyBand) return false;
      if (weakOnly && !cluster.weak_signal_flag) return false;
      return true;
    });

    return [...clusters].sort((left, right) => {
      switch (sortBy) {
        case 'momentum':
          return right.momentum_score - left.momentum_score;
        case 'novelty':
          return right.novelty_score - left.novelty_score;
        case 'size':
          return right.item_count - left.item_count;
        case 'quality':
          return right.cluster_quality.score - left.cluster_quality.score;
        case 'maturity':
          return right.maturity_score - left.maturity_score;
        case 'impact':
        default:
          return right.impact_score - left.impact_score;
      }
    });
  });

  readonly filteredArticles = computed(() => {
    const d = this.data();
    if (!d) return [];

    const clusterIndex = new Map(this.filteredClusters().map((cluster) => [cluster.cluster_id, cluster]));
    return d.articles.filter((article) => {
      const sourceType = this.filterSourceType();
      if (sourceType && article.source_type !== sourceType) return false;
      if (article.cluster_id === 'sin_cluster') {
        return !this.weakSignalsOnly();
      }
      return clusterIndex.has(article.cluster_id);
    });
  });

  readonly selectedClusterArticles = computed(() => {
    const cluster = this.selectedCluster();
    if (!cluster) return [];
    const ids = new Set(cluster.articles);
    return this.filteredArticles().filter((article) => ids.has(article.id));
  });

  readonly selectedClusterCard = computed(() => {
    const cluster = this.selectedCluster();
    const d = this.data();
    if (!cluster || !d?.cluster_cards) return null;
    return d.cluster_cards.find((card) => card.cluster_id === cluster.cluster_id) ?? null;
  });

  readonly highlightCards = computed(() => {
    const d = this.data();
    return (d?.cluster_cards ?? []).slice(0, 6);
  });

  readonly activeFilterSummary = computed(() => {
    const active: string[] = [];
    if (this.filterCategory()) active.push(`Categoría: ${this.filterCategory()}`);
    if (this.filterSourceType()) active.push(`Fuente: ${this.filterSourceType()}`);
    if (this.filterMaturityStage()) active.push(`Madurez: ${this.filterMaturityStage()}`);
    if (this.filterHypeStage()) active.push(`Hype: ${this.filterHypeStage()}`);
    if (this.filterSignalState()) active.push(`Estado: ${this.filterSignalState()}`);
    if (this.filterComparativeStatus()) active.push(`Comparativo: ${this.filterComparativeStatus()}`);
    if (this.filterNoveltyBand()) active.push(`Novedad: ${this.filterNoveltyBand()}`);
    if (this.weakSignalsOnly()) active.push('Solo weak signals');
    active.push(`Orden: ${this.sortBy()}`);
    return active;
  });

  constructor(
    private http: HttpClient,
    @Inject(API_BASE_URL) private baseUrl: string,
  ) {}

  load(): void {
    this.loading.set(true);
    this.error.set(null);

    this.http.get<TrendmapData>(`${this.baseUrl}/trendmap/`).subscribe({
      next: (response) => {
        this.data.set(response);
        this.selectedCluster.set(response.clusters[0] ?? null);
        this.syncSelectedCluster();
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
    this.syncSelectedCluster();
  }

  setFilterSourceType(sourceType: string | null): void {
    this.filterSourceType.set(sourceType);
    this.syncSelectedCluster();
  }

  setFilterMaturityStage(stage: string | null): void {
    this.filterMaturityStage.set(stage);
    this.syncSelectedCluster();
  }

  setFilterHypeStage(stage: LifecycleStage | null): void {
    this.filterHypeStage.set(stage);
    this.syncSelectedCluster();
  }

  setFilterSignalState(state: string | null): void {
    this.filterSignalState.set(state);
    this.syncSelectedCluster();
  }

  setFilterComparativeStatus(status: 'new' | 'accelerating' | 'cooling' | 'stable' | null): void {
    this.filterComparativeStatus.set(status);
    this.syncSelectedCluster();
  }

  setFilterNoveltyBand(band: string | null): void {
    this.filterNoveltyBand.set(band);
    this.syncSelectedCluster();
  }

  setWeakSignalsOnly(enabled: boolean): void {
    this.weakSignalsOnly.set(enabled);
    this.syncSelectedCluster();
  }

  setSortBy(sortBy: ClusterSort): void {
    this.sortBy.set(sortBy);
    this.syncSelectedCluster();
  }

  clearFilters(): void {
    this.filterCategory.set(null);
    this.filterSourceType.set(null);
    this.filterMaturityStage.set(null);
    this.filterHypeStage.set(null);
    this.filterSignalState.set(null);
    this.filterComparativeStatus.set(null);
    this.filterNoveltyBand.set(null);
    this.weakSignalsOnly.set(false);
    this.sortBy.set('impact');
    this.syncSelectedCluster();
  }

  private syncSelectedCluster(): void {
    const current = this.selectedCluster();
    const visible = this.filteredClusters();
    if (visible.length === 0) {
      this.selectedCluster.set(null);
      return;
    }
    if (!current || !visible.some((cluster) => cluster.cluster_id === current.cluster_id)) {
      this.selectedCluster.set(visible[0]);
    }
  }
}
