import { DecimalPipe } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, Inject, OnInit, computed, inject, signal } from '@angular/core';
import { API_BASE_URL } from '../../../../../config/api.token';
import { DARK_THEME, LifecycleStage, RiskmapCluster, RiskmapData } from '../../../../../domain/noticias/models';

type RiskSort = 'severity' | 'momentum' | 'persistence' | 'impact' | 'novelty' | 'size';

@Component({
  selector: 'app-riskmap',
  standalone: true,
  imports: [DecimalPipe],
  templateUrl: './riskmap.component.html',
})
export class RiskmapComponent implements OnInit {
  private readonly http = inject(HttpClient);
  readonly theme = DARK_THEME;
  readonly axisTicks = [0, 25, 50, 75, 100];
  readonly sortOptions = [
    { value: 'severity', label: 'Severidad' },
    { value: 'momentum', label: 'Momentum' },
    { value: 'persistence', label: 'Persistencia' },
    { value: 'impact', label: 'Impacto' },
    { value: 'novelty', label: 'Novedad' },
    { value: 'size', label: 'Tamano' },
  ] as const;

  readonly snapshot = signal<RiskmapData | null>(null);
  readonly loading = signal(false);
  readonly running = signal(false);
  readonly error = signal<string | null>(null);
  readonly selectedCluster = signal<RiskmapCluster | null>(null);
  readonly filterCategory = signal<string | null>(null);
  readonly filterSourceType = signal<string | null>(null);
  readonly filterHypeStage = signal<LifecycleStage | null>(null);
  readonly weakSignalsOnly = signal(false);
  readonly sortBy = signal<RiskSort>('severity');

  readonly categories = computed(() => this.snapshot()?.filters_metadata?.categories ?? [...new Set((this.snapshot()?.clusters ?? []).map((cluster) => cluster.category))]);
  readonly sourceTypes = computed(() => this.snapshot()?.filters_metadata?.source_types ?? [...new Set((this.snapshot()?.documents ?? []).map((doc) => doc.source_type))]);
  readonly hypeStages = computed(() => this.snapshot()?.filters_metadata?.hype_stages ?? [...new Set((this.snapshot()?.clusters ?? []).map((cluster) => cluster.hype_stage))]);
  readonly taxonomyBreakdown = computed(() => this.snapshot()?.taxonomy_breakdown ?? []);
  readonly sourceMix = computed(() => (this.snapshot()?.charts?.['source_mix'] as Array<{ source: string; count: number }> | undefined) ?? []);
  readonly monthlyVolume = computed(() => (this.snapshot()?.charts?.['monthly_volume'] as Array<{ bucket: string; count: number }> | undefined) ?? []);
  readonly topSignals = computed(() => this.snapshot()?.risk_signals ?? []);

  readonly filteredClusters = computed(() => {
    const data = this.snapshot();
    if (!data) return [];
    const items = data.clusters.filter((cluster) => {
      if (this.filterCategory() && cluster.category !== this.filterCategory()) return false;
      if (this.filterHypeStage() && cluster.hype_stage !== this.filterHypeStage()) return false;
      if (this.weakSignalsOnly() && !cluster.weak_signal_flag) return false;
      if (this.filterSourceType()) {
        const hasSource = data.documents.some((doc) => doc.cluster_id === cluster.cluster_id && doc.source_type === this.filterSourceType());
        if (!hasSource) return false;
      }
      return true;
    });
    return [...items].sort((a, b) => this.sortValue(b, this.sortBy()) - this.sortValue(a, this.sortBy()));
  });

  readonly filteredDocuments = computed(() => {
    const data = this.snapshot();
    if (!data) return [];
    const visible = new Set(this.filteredClusters().map((cluster) => cluster.cluster_id));
    return data.documents.filter((doc) => {
      if (this.filterSourceType() && doc.source_type !== this.filterSourceType()) return false;
      if (doc.cluster_id === 'sin_cluster') return !this.weakSignalsOnly();
      return visible.has(doc.cluster_id);
    });
  });

  readonly selectedOrFilteredDocuments = computed(() => {
    const cluster = this.selectedCluster();
    if (!cluster) return this.filteredDocuments();
    const ids = new Set(cluster.articles);
    const selected = this.filteredDocuments().filter((doc) => ids.has(doc.id) || doc.cluster_id === cluster.cluster_id);
    return selected.length > 0 ? selected : this.filteredDocuments();
  });

  readonly scatterPoints = computed(() => {
    const items = this.filteredClusters();
    const maxCount = Math.max(...items.map((cluster) => cluster.item_count), 1);
    return items.map((cluster) => ({
      cluster,
      x: this.scatterX(cluster.risk_severity),
      y: this.scatterY(cluster.momentum_score),
      r: 8 + (cluster.item_count / maxCount) * 18,
      color: this.colorFor(cluster.category),
    }));
  });

  readonly activeFilterSummary = computed(() => {
    const tags: string[] = [];
    if (this.filterCategory()) tags.push(`Categoria: ${this.filterCategory()}`);
    if (this.filterSourceType()) tags.push(`Fuente: ${this.filterSourceType()}`);
    if (this.filterHypeStage()) tags.push(`Hype: ${this.stageLabel(this.filterHypeStage()!)}`);
    if (this.weakSignalsOnly()) tags.push('Solo weak signals');
    tags.push(`Orden: ${this.sortBy()}`);
    return tags;
  });

  constructor(@Inject(API_BASE_URL) private baseUrl: string) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.http.get<RiskmapData>(`${this.baseUrl}/riskmap/latest`).subscribe({
      next: (snapshot) => {
        this.snapshot.set(snapshot);
        this.selectedCluster.set(snapshot.clusters[0] ?? null);
        this.syncSelectedCluster();
        this.loading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(err.error?.detail ?? `Error: ${err.status}`);
        this.snapshot.set(null);
        this.loading.set(false);
      },
    });
  }

  runRiskmap(): void {
    this.running.set(true);
    this.error.set(null);
    this.http.post(`${this.baseUrl}/riskmap/run`, {
      catalog_path: 'catalog.yaml',
      days: 7,
      max_items_per_source: 20,
      classifier_mode: 'rules',
      window_months: 6,
      force_snapshot: false,
    }).subscribe({
      next: () => {
        this.running.set(false);
        this.load();
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(err.error?.detail ?? 'No se pudo iniciar el risk mapping.');
        this.running.set(false);
      },
    });
  }

  kpis() {
    const data = this.snapshot();
    if (!data) return [];
    return [
      { label: 'Documentos', value: data.summary.total_documents ?? data.meta.total_filtered },
      { label: 'Clusters', value: data.meta.total_clusters },
      { label: 'Weak', value: data.quality_checks?.weak_signal_clusters ?? 0 },
      { label: 'Taxonomia', value: `${data.quality_checks?.taxonomy_coverage ?? 0}%` },
      { label: 'Sin cluster', value: data.summary.unclustered_documents ?? 0 },
      { label: 'Fuentes', value: data.filters_metadata?.sources.length ?? 0 },
    ];
  }

  highlightClusters(): RiskmapCluster[] {
    return this.filteredClusters().slice(0, 6);
  }

  selectedScoreRows() {
    const cluster = this.selectedCluster();
    if (!cluster) return [];
    return [
      { label: 'Severidad', score: cluster.risk_severity_breakdown?.score ?? 0, formula: cluster.risk_severity_breakdown?.formula ?? '' },
      { label: 'Impacto', score: cluster.impact_score_breakdown.score, formula: cluster.impact_score_breakdown.formula },
      { label: 'Madurez', score: cluster.maturity_score_breakdown.score, formula: cluster.maturity_score_breakdown.formula },
      { label: 'Momentum', score: cluster.momentum_score_breakdown.score, formula: cluster.momentum_score_breakdown.formula },
    ];
  }

  selectCluster(cluster: RiskmapCluster | null): void {
    this.selectedCluster.set(cluster);
  }

  setFilterCategory(value: string | null): void { this.filterCategory.set(value); this.syncSelectedCluster(); }
  setFilterSourceType(value: string | null): void { this.filterSourceType.set(value); this.syncSelectedCluster(); }
  setFilterHypeStage(value: LifecycleStage | null): void { this.filterHypeStage.set(value); this.syncSelectedCluster(); }
  setWeakSignalsOnly(value: boolean): void { this.weakSignalsOnly.set(value); this.syncSelectedCluster(); }
  setSortBy(value: RiskSort): void { this.sortBy.set(value); this.syncSelectedCluster(); }

  clearFilters(): void {
    this.filterCategory.set(null);
    this.filterSourceType.set(null);
    this.filterHypeStage.set(null);
    this.weakSignalsOnly.set(false);
    this.sortBy.set('severity');
    this.syncSelectedCluster();
  }

  onSelectValue(event: Event): string | null { return (event.target as HTMLSelectElement).value || null; }
  onStageValue(event: Event): LifecycleStage | null { return ((event.target as HTMLSelectElement).value as LifecycleStage) || null; }
  onSortValue(event: Event): RiskSort { return (event.target as HTMLSelectElement).value as RiskSort; }
  onCheckboxValue(event: Event): boolean { return (event.target as HTMLInputElement).checked; }

  stageLabel(value: string): string { return value.replaceAll('_', ' '); }
  shortLabel(value: string, maxLength: number): string { return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value; }

  stageBadge(value: string): string {
    const base = 'rounded-full border px-2 py-1 text-[10px] font-medium ';
    if (value === 'weak_signal') return base + 'border-amber-500/40 bg-amber-500/10 text-amber-300';
    if (value === 'correction') return base + 'border-rose-500/40 bg-rose-500/10 text-rose-300';
    if (value === 'productive_adoption' || value === 'consolidation') return base + 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300';
    return base + 'border-sky-500/40 bg-sky-500/10 text-sky-300';
  }

  severityBadge(value: 'H' | 'M' | 'L'): string {
    const base = 'rounded-full border px-2 py-1 text-[10px] font-medium ';
    if (value === 'H') return base + 'border-rose-500/40 bg-rose-500/10 text-rose-300';
    if (value === 'M') return base + 'border-amber-500/40 bg-amber-500/10 text-amber-300';
    return base + 'border-sky-500/40 bg-sky-500/10 text-sky-300';
  }

  clusterCardClass(cluster: RiskmapCluster): string {
    return this.selectedCluster()?.cluster_id === cluster.cluster_id ? 'border-amber-500/70 bg-dark-bg' : 'border-dark-border bg-dark-bg/40 hover:border-dark-muted hover:bg-dark-bg/70';
  }

  scatterX(value: number): number { return 56 + (Math.max(0, Math.min(100, value)) / 100) * 528; }
  scatterY(value: number): number { return 308 - (Math.max(0, Math.min(100, value)) / 100) * 272; }
  bubbleOpacity(cluster: RiskmapCluster): number { return !this.selectedCluster() || this.selectedCluster()?.cluster_id === cluster.cluster_id ? 0.9 : 0.28; }
  ratio(value: number, max: number): number { return !max ? 0 : Math.max(0, Math.min(100, (value / max) * 100)); }
  taxonomyMax(): number { return Math.max(...this.taxonomyBreakdown().map((item) => item.score), 0); }
  sourceMixMax(): number { return Math.max(...this.sourceMix().map((item) => item.count), 0); }
  monthlyVolumeMax(): number { return Math.max(...this.monthlyVolume().map((item) => item.count), 0); }

  colorFor(value: string): string {
    const palette = ['#38bdf8', '#f59e0b', '#34d399', '#f87171', '#818cf8', '#f472b6'];
    const hash = [...value].reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return palette[hash % palette.length];
  }

  private sortValue(cluster: RiskmapCluster, sort: RiskSort): number {
    switch (sort) {
      case 'momentum': return cluster.momentum_score;
      case 'persistence': return cluster.persistence_score;
      case 'impact': return cluster.impact_score;
      case 'novelty': return cluster.novelty_score;
      case 'size': return cluster.item_count;
      case 'severity':
      default: return cluster.risk_severity;
    }
  }

  private syncSelectedCluster(): void {
    const visible = this.filteredClusters();
    if (visible.length === 0) return this.selectedCluster.set(null);
    if (!this.selectedCluster() || !visible.some((cluster) => cluster.cluster_id === this.selectedCluster()?.cluster_id)) {
      this.selectedCluster.set(visible[0]);
    }
  }
}
