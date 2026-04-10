import { DecimalPipe } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, Inject, OnInit, computed, inject, signal } from '@angular/core';

import { API_BASE_URL } from '../../../../../config/api.token';
import { DARK_THEME, LifecycleStage, RiskmapCluster, RiskmapData } from '../../../../../domain/noticias/models';
import { RiskmapD3ScatterComponent } from './riskmap-d3-scatter.component';
import { RiskmapDetailComponent } from './riskmap-detail.component';
import { RiskmapHypeComponent } from './riskmap-hype.component';
import { RiskmapImpactComponent } from './riskmap-impact.component';
import { RiskmapMethodologyComponent } from './riskmap-methodology.component';
import { RiskmapOverviewComponent } from './riskmap-overview.component';
import { RiskmapSidebarComponent } from './riskmap-sidebar.component';

type RiskSort = 'severity' | 'momentum' | 'persistence' | 'impact' | 'novelty' | 'size';
type RiskBand = 'low' | 'medium' | 'high';
type RiskTabId = 'resumen' | 'mapa' | 'impacto' | 'hype' | 'detalle' | 'metodologia';

const SOURCE_TYPE_LABELS: Record<string, string> = {
  news: 'Noticias',
  rss: 'Articulos y blogs',
  paper: 'Articulos academicos',
  pdf: 'Documentos tecnicos',
  patent: 'Patentes',
  institutional_report: 'Reportes institucionales',
};

const RISK_TABS: Array<{ id: RiskTabId; label: string }> = [
  { id: 'resumen', label: 'Resumen' },
  { id: 'mapa', label: 'Mapa' },
  { id: 'impacto', label: 'Impacto' },
  { id: 'hype', label: 'Ciclo de madurez' },
  { id: 'detalle', label: 'Detalle' },
  { id: 'metodologia', label: 'Metodologia' },
];

@Component({
  selector: 'app-riskmap',
  standalone: true,
  imports: [
    DecimalPipe,
    RiskmapOverviewComponent,
    RiskmapD3ScatterComponent,
    RiskmapImpactComponent,
    RiskmapHypeComponent,
    RiskmapDetailComponent,
    RiskmapMethodologyComponent,
    RiskmapSidebarComponent,
  ],
  templateUrl: './riskmap.component.html',
})
export class RiskmapComponent implements OnInit {
  private readonly http = inject(HttpClient);

  readonly theme = DARK_THEME;
  readonly sortOptions = [
    { value: 'severity', label: 'Severidad' },
    { value: 'momentum', label: 'Dinamica' },
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

  readonly showSidebar = computed(() => {
    const tab = this.activeTab();
    return tab === 'mapa' || tab === 'detalle';
  });

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
        const hasSource = data.documents.some(
          (doc) => doc.cluster_id === cluster.cluster_id && doc.source_type === this.filterSourceType(),
        );
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
    const selected = this.filteredDocuments().filter(
      (doc) => ids.has(doc.id) || doc.cluster_id === cluster.cluster_id,
    );
    return selected.length > 0 ? selected : this.filteredDocuments();
  });

  readonly activeFilterSummary = computed(() => {
    const tags: string[] = [];
    if (this.filterCategory()) tags.push(`Categoria: ${this.filterCategory()}`);
    if (this.filterSourceType()) tags.push(`Fuente: ${this.sourceTypeLabel(this.filterSourceType()!)}`);
    if (this.filterMaturityStage()) tags.push(`Madurez: ${this.stageLabel(this.filterMaturityStage()!)}`);
    if (this.filterHypeStage()) tags.push(`Etapa: ${this.stageLabel(this.filterHypeStage()!)}`);
    if (this.filterSeverityBand()) tags.push(`Severidad: ${this.filterSeverityBand()}`);
    if (this.filterNoveltyBand()) tags.push(`Novedad: ${this.filterNoveltyBand()}`);
    if (this.weakSignalsOnly()) tags.push('Solo señales tempranas');
    tags.push(`Orden: ${this.sortBy()}`);
    return tags;
  });

  constructor(@Inject(API_BASE_URL) private readonly baseUrl: string) {}

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

    this.http
      .post(`${this.baseUrl}/riskmap/run`, {
        catalog_path: 'catalog.yaml',
        days: 7,
        max_items_per_source: 60,
        classifier_mode: 'llm',
        window_months: 6,
        force_snapshot: false,
        generate_snapshot_after_ingest: false,
      })
      .subscribe({
        next: (response: any) => {
          this.ingesting.set(false);
          this.statusMessage.set(
            `Ingesta de riesgos iniciada. Id de ejecucion: ${response?.run_id ?? 'pendiente'}. Genera el reporte cuando termine la ejecucion.`,
          );
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

    this.http
      .post(`${this.baseUrl}/riskmap/generate`, {
        window_months: 6,
        force: true,
      })
      .subscribe({
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

  highlightClusters(): RiskmapCluster[] {
    return this.filteredClusters().slice(0, 6);
  }

  selectedScoreRows() {
    const cluster = this.selectedCluster();
    if (!cluster) return [];

    return [
      {
        label: 'Severidad',
        score: cluster.risk_severity_breakdown?.score ?? cluster.risk_severity,
        formula: cluster.risk_severity_breakdown?.formula ?? '',
      },
      {
        label: 'Persistencia',
        score: cluster.persistence_score_breakdown?.score ?? cluster.persistence_score,
        formula: cluster.persistence_score_breakdown?.formula ?? '',
      },
      {
        label: 'Impacto',
        score: cluster.impact_score_breakdown?.score ?? cluster.impact_score,
        formula: cluster.impact_score_breakdown?.formula ?? '',
      },
      {
        label: 'Madurez',
        score: cluster.maturity_score_breakdown?.score ?? cluster.maturity_score,
        formula: cluster.maturity_score_breakdown?.formula ?? '',
      },
      {
        label: 'Dinamica',
        score: cluster.momentum_score_breakdown?.score ?? cluster.momentum_score,
        formula: cluster.momentum_score_breakdown?.formula ?? '',
      },
      {
        label: 'Novedad',
        score: cluster.novelty_score_breakdown?.score ?? cluster.novelty_score,
        formula: cluster.novelty_score_breakdown?.formula ?? '',
      },
      {
        label: 'Incertidumbre',
        score: cluster.uncertainty_score_breakdown?.score ?? cluster.uncertainty_score,
        formula: cluster.uncertainty_score_breakdown?.formula ?? '',
      },
    ];
  }

  selectCluster(cluster: RiskmapCluster | null): void {
    this.selectedCluster.set(cluster);
  }

  setFilterCategory(value: string | null): void {
    this.filterCategory.set(value);
    this.syncSelectedCluster();
  }

  setFilterSourceType(value: string | null): void {
    this.filterSourceType.set(value);
    this.syncSelectedCluster();
  }

  setFilterMaturityStage(value: string | null): void {
    this.filterMaturityStage.set(value);
    this.syncSelectedCluster();
  }

  setFilterHypeStage(value: LifecycleStage | null): void {
    this.filterHypeStage.set(value);
    this.syncSelectedCluster();
  }

  setFilterSeverityBand(value: RiskBand | null): void {
    this.filterSeverityBand.set(value);
    this.syncSelectedCluster();
  }

  setFilterNoveltyBand(value: RiskBand | null): void {
    this.filterNoveltyBand.set(value);
    this.syncSelectedCluster();
  }

  setWeakSignalsOnly(value: boolean): void {
    this.weakSignalsOnly.set(value);
    this.syncSelectedCluster();
  }

  setSortBy(value: RiskSort): void {
    this.sortBy.set(value);
    this.syncSelectedCluster();
  }

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
    if (normalized.includes('build_riskmap') || normalized.includes('risk_pipeline_adapter')) {
      return 'Motor analitico de riesgos v2';
    }
    if (normalized.includes('analytics_methodology')) {
      return 'Motor analitico avanzado';
    }
    return value.replaceAll('_', ' ');
  }

  stageLabel(value: string): string {
    return value.replaceAll('_', ' ');
  }

  sourceTypeLabel(value: string): string {
    return SOURCE_TYPE_LABELS[value] ?? value.replaceAll('_', ' ');
  }

  private sortValue(cluster: RiskmapCluster, sort: RiskSort): number {
    switch (sort) {
      case 'momentum':
        return cluster.momentum_score;
      case 'persistence':
        return cluster.persistence_score;
      case 'impact':
        return cluster.impact_score;
      case 'novelty':
        return cluster.novelty_score;
      case 'size':
        return cluster.item_count;
      case 'severity':
      default:
        return cluster.risk_severity;
    }
  }

  private syncSelectedCluster(): void {
    const visible = this.filteredClusters();
    if (visible.length === 0) {
      this.selectedCluster.set(null);
      return;
    }

    const selected = this.selectedCluster();
    if (!selected || !visible.some((cluster) => cluster.cluster_id === selected.cluster_id)) {
      this.selectedCluster.set(visible[0]);
    }
  }
}
