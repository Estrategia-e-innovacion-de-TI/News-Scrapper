import { DecimalPipe } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, Inject, OnInit, computed, inject, signal } from '@angular/core';
import { API_BASE_URL } from '../../../../../config/api.token';
import { DARK_THEME, LifecycleStage, RiskmapCluster, RiskmapData } from '../../../../../domain/noticias/models';
import { RiskmapDetailComponent } from './riskmap-detail.component';
import { RiskmapImpactComponent } from './riskmap-impact.component';
import { RiskmapMapComponent } from './riskmap-map.component';
import { RiskmapOverviewComponent } from './riskmap-overview.component';

type RiskSort = 'severity' | 'momentum' | 'persistence' | 'impact' | 'novelty' | 'size';
type RiskBand = 'low' | 'medium' | 'high';
type RiskTabId = 'resumen' | 'mapa' | 'impacto' | 'detalle';

const RISK_TABS: Array<{ id: RiskTabId; label: string }> = [
  { id: 'resumen', label: 'Resumen' },
  { id: 'mapa', label: 'Mapa' },
  { id: 'impacto', label: 'Impacto de riesgo' },
  { id: 'detalle', label: 'Detalle' },
];

@Component({
  selector: 'app-riskmap',
  standalone: true,
  imports: [
    DecimalPipe,
    RiskmapDetailComponent,
    RiskmapImpactComponent,
    RiskmapMapComponent,
    RiskmapOverviewComponent,
  ],
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
  readonly tabs = RISK_TABS;
  readonly activeTab = signal<RiskTabId>('resumen');

  readonly snapshot = signal<RiskmapData | null>(null);
  readonly loading = signal(false);
  readonly ingesting = signal(false);
  readonly generating = signal(false);
  readonly error = signal<string | null>(null);
  readonly statusMessage = signal<string | null>(null);
  readonly selectedCluster = signal<RiskmapCluster | null>(null);
  readonly filterCategory = signal<string | null>(null);
  readonly filterSourceType = signal<string | null>(null);
  readonly filterMaturityStage = signal<string | null>(null);
  readonly filterHypeStage = signal<LifecycleStage | null>(null);
  readonly filterSeverityBand = signal<RiskBand | null>(null);
  readonly filterNoveltyBand = signal<RiskBand | null>(null);
  readonly weakSignalsOnly = signal(false);
  readonly sortBy = signal<RiskSort>('severity');

  readonly categories = computed(() => this.snapshot()?.filters_metadata?.categories ?? [...new Set((this.snapshot()?.clusters ?? []).map((cluster) => cluster.category))]);
  readonly sourceTypes = computed(() => this.snapshot()?.filters_metadata?.source_types ?? [...new Set((this.snapshot()?.documents ?? []).map((doc) => doc.source_type))]);
  readonly maturityStages = computed(() => this.snapshot()?.filters_metadata?.maturity_stages ?? [...new Set((this.snapshot()?.clusters ?? []).map((cluster) => cluster.maturity_stage))]);
  readonly hypeStages = computed(() => this.snapshot()?.filters_metadata?.hype_stages ?? [...new Set((this.snapshot()?.clusters ?? []).map((cluster) => cluster.hype_stage))]);
  readonly severityBands = computed<RiskBand[]>(() => ((this.snapshot()?.filters_metadata?.severity_bands as RiskBand[] | undefined) ?? ['low', 'medium', 'high']));
  readonly noveltyBands = computed<RiskBand[]>(() => ((this.snapshot()?.filters_metadata?.novelty_bands as RiskBand[] | undefined) ?? ['low', 'medium', 'high']));
  readonly taxonomyBreakdown = computed(() => this.snapshot()?.taxonomy_breakdown ?? []);
  readonly sourceMix = computed(() => (this.snapshot()?.charts?.['source_mix'] as Array<{ source: string; count: number }> | undefined) ?? []);
  readonly monthlyVolume = computed(() => (this.snapshot()?.charts?.['monthly_volume'] as Array<{ bucket: string; count: number }> | undefined) ?? []);
  readonly topSignals = computed(() => this.snapshot()?.risk_signals ?? []);

  readonly filteredClusters = computed(() => {
    const data = this.snapshot();
    if (!data) return [];
    const items = data.clusters.filter((cluster) => {
      if (this.filterCategory() && cluster.category !== this.filterCategory()) return false;
      if (this.filterMaturityStage() && cluster.maturity_stage !== this.filterMaturityStage()) return false;
      if (this.filterHypeStage() && cluster.hype_stage !== this.filterHypeStage()) return false;
      if (this.filterSeverityBand() && cluster.severity_band !== this.filterSeverityBand()) return false;
      if (this.filterNoveltyBand() && cluster.novelty_band !== this.filterNoveltyBand()) return false;
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

  readonly clusterMapPoints = computed(() => {
    const items = this.filteredClusters();
    const maxCount = Math.max(...items.map((cluster) => cluster.item_count), 1);
    const xs = items.map((cluster) => cluster.coords?.x ?? 0);
    const ys = items.map((cluster) => cluster.coords?.y ?? 0);
    const minX = Math.min(...xs, 0);
    const maxX = Math.max(...xs, 1);
    const minY = Math.min(...ys, 0);
    const maxY = Math.max(...ys, 1);
    return items.map((cluster) => ({
      cluster,
      x: this.scaleToRange(cluster.coords?.x ?? 0, minX, maxX, 56, 584),
      y: this.scaleToRange(cluster.coords?.y ?? 0, minY, maxY, 308, 36),
      r: 9 + (cluster.item_count / maxCount) * 20,
      color: this.colorFor(cluster.category),
    }));
  });

  readonly activeFilterSummary = computed(() => {
    const tags: string[] = [];
    if (this.filterCategory()) tags.push(`Categoria: ${this.filterCategory()}`);
    if (this.filterSourceType()) tags.push(`Fuente: ${this.filterSourceType()}`);
    if (this.filterMaturityStage()) tags.push(`Madurez: ${this.stageLabel(this.filterMaturityStage()!)}`);
    if (this.filterHypeStage()) tags.push(`Hype: ${this.stageLabel(this.filterHypeStage()!)}`);
    if (this.filterSeverityBand()) tags.push(`Severidad: ${this.filterSeverityBand()}`);
    if (this.filterNoveltyBand()) tags.push(`Novedad: ${this.filterNoveltyBand()}`);
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
    this.ingesting.set(true);
    this.error.set(null);
    this.statusMessage.set(null);
    this.http.post(`${this.baseUrl}/riskmap/run`, {
      catalog_path: 'catalog.yaml',
      days: 7,
      max_items_per_source: 60,
      classifier_mode: 'llm',
      window_months: 6,
      force_snapshot: false,
      generate_snapshot_after_ingest: false,
    }).subscribe({
      next: (response: any) => {
        this.ingesting.set(false);
        this.statusMessage.set(`Ingesta de riesgos iniciada. Run ID: ${response?.run_id ?? 'pendiente'}. Genera el reporte cuando termine la ejecucion.`);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(err.error?.detail ?? 'No se pudo iniciar la ingesta de riesgos.');
        this.ingesting.set(false);
      },
    });
  }

  generateRiskmap(): void {
    this.generating.set(true);
    this.error.set(null);
    this.statusMessage.set(null);
    this.http.post(`${this.baseUrl}/riskmap/generate`, {
      window_months: 6,
      force: true,
    }).subscribe({
      next: () => {
        this.generating.set(false);
        this.statusMessage.set('Reporte de riesgos generado con el corpus disponible.');
        this.load();
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(err.error?.detail ?? 'No se pudo generar el reporte de riesgos.');
        this.generating.set(false);
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
      { label: 'Persistencia', score: cluster.persistence_score_breakdown?.score ?? cluster.persistence_score ?? 0, formula: cluster.persistence_score_breakdown?.formula ?? '' },
      { label: 'Impacto', score: cluster.impact_score_breakdown.score, formula: cluster.impact_score_breakdown.formula },
      { label: 'Madurez', score: cluster.maturity_score_breakdown.score, formula: cluster.maturity_score_breakdown.formula },
      { label: 'Momentum', score: cluster.momentum_score_breakdown.score, formula: cluster.momentum_score_breakdown.formula },
      { label: 'Novedad', score: cluster.novelty_score_breakdown.score, formula: cluster.novelty_score_breakdown.formula },
      { label: 'Incertidumbre', score: cluster.uncertainty_score_breakdown.score, formula: cluster.uncertainty_score_breakdown.formula },
    ];
  }

  selectCluster(cluster: RiskmapCluster | null): void {
    this.selectedCluster.set(cluster);
  }

  setFilterCategory(value: string | null): void { this.filterCategory.set(value); this.syncSelectedCluster(); }
  setFilterSourceType(value: string | null): void { this.filterSourceType.set(value); this.syncSelectedCluster(); }
  setFilterMaturityStage(value: string | null): void { this.filterMaturityStage.set(value); this.syncSelectedCluster(); }
  setFilterHypeStage(value: LifecycleStage | null): void { this.filterHypeStage.set(value); this.syncSelectedCluster(); }
  setFilterSeverityBand(value: RiskBand | null): void { this.filterSeverityBand.set(value); this.syncSelectedCluster(); }
  setFilterNoveltyBand(value: RiskBand | null): void { this.filterNoveltyBand.set(value); this.syncSelectedCluster(); }
  setWeakSignalsOnly(value: boolean): void { this.weakSignalsOnly.set(value); this.syncSelectedCluster(); }
  setSortBy(value: RiskSort): void { this.sortBy.set(value); this.syncSelectedCluster(); }

  clearFilters(): void {
    this.filterCategory.set(null);
    this.filterSourceType.set(null);
    this.filterMaturityStage.set(null);
    this.filterHypeStage.set(null);
    this.filterSeverityBand.set(null);
    this.filterNoveltyBand.set(null);
    this.weakSignalsOnly.set(false);
    this.sortBy.set('severity');
    this.syncSelectedCluster();
  }

  onSelectValue(event: Event): string | null { return (event.target as HTMLSelectElement).value || null; }
  onStageValue(event: Event): LifecycleStage | null { return ((event.target as HTMLSelectElement).value as LifecycleStage) || null; }
  onBandValue(event: Event): RiskBand | null { return ((event.target as HTMLSelectElement).value as RiskBand) || null; }
  onSortValue(event: Event): RiskSort { return (event.target as HTMLSelectElement).value as RiskSort; }
  onCheckboxValue(event: Event): boolean { return (event.target as HTMLInputElement).checked; }

  stageLabel(value: string): string { return value.replaceAll('_', ' '); }
  shortLabel(value: string, maxLength: number): string { return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value; }

  tabClass(tabId: RiskTabId): string {
    const base = 'px-4 py-2 text-sm font-medium transition-colors cursor-pointer ';
    if (this.activeTab() === tabId) {
      return base + 'text-dark-accent border-b-2 border-dark-accent';
    }
    return base + 'text-dark-muted hover:text-dark-text';
  }

  methodologyLabel(value: string | undefined): string {
    if (!value) return '';
    const normalized = value.toLowerCase();
    if (normalized.includes('build_trendmap') || normalized.includes('trend_pipeline_adapter')) {
      return 'Motor analitico de tendencias v2';
    }
    if (normalized.includes('analytics_methodology')) {
      return 'Motor analitico avanzado';
    }
    return value.replaceAll('_', ' ');
  }

  stageBadge(value: string): string {
    const base = 'rounded-full border px-2 py-1 text-[10px] font-medium ';
    if (value === 'weak_signal') return base + 'border-yellow-500 bg-yellow-100 text-yellow-900';
    if (value === 'correction') return base + 'border-rose-500 bg-rose-50 text-rose-700';
    if (value === 'productive_adoption' || value === 'consolidation') return base + 'border-emerald-500 bg-emerald-50 text-emerald-700';
    return base + 'border-sky-500 bg-sky-50 text-sky-700';
  }

  severityBadge(value: 'H' | 'M' | 'L'): string {
    const base = 'rounded-full border px-2 py-1 text-[10px] font-medium ';
    if (value === 'H') return base + 'border-rose-500 bg-rose-50 text-rose-700';
    if (value === 'M') return base + 'border-yellow-500 bg-yellow-100 text-yellow-900';
    return base + 'border-sky-500 bg-sky-50 text-sky-700';
  }

  clusterCardClass(cluster: RiskmapCluster): string {
    return this.selectedCluster()?.cluster_id === cluster.cluster_id ? 'border-yellow-500 bg-yellow-50' : 'border-dark-border bg-white hover:border-yellow-400 hover:bg-yellow-50';
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

  private scaleToRange(value: number, min: number, max: number, outMin: number, outMax: number): number {
    if (max === min) {
      return (outMin + outMax) / 2;
    }
    const ratio = (value - min) / (max - min);
    return outMin + Math.max(0, Math.min(1, ratio)) * (outMax - outMin);
  }

  private syncSelectedCluster(): void {
    const visible = this.filteredClusters();
    if (visible.length === 0) return this.selectedCluster.set(null);
    if (!this.selectedCluster() || !visible.some((cluster) => cluster.cluster_id === this.selectedCluster()?.cluster_id)) {
      this.selectedCluster.set(visible[0]);
    }
  }
}
