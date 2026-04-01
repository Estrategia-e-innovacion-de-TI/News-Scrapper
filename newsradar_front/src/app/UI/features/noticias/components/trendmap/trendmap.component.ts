import { DecimalPipe } from '@angular/common';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { TrendmapSignalService } from '../../../../../infrastructure/noticias/services/trendmap.service';
import { TrendmapOverviewComponent } from './overview.component';
import { D3ScatterComponent } from './d3-scatter.component';
import { TrendmapImpactComponent } from './impact.component';
import { HypeCycleComponent } from './hype-cycle.component';
import { TrendmapDetailComponent } from './detail.component';
import { TrendmapMethodologyComponent } from './methodology.component';
import { TrendmapSidebarComponent } from './sidebar.component';

type TabId = 'resumen' | 'mapa' | 'impacto' | 'hype' | 'detalle' | 'metodologia';

interface Tab {
  id: TabId;
  label: string;
}

const TABS: Tab[] = [
  { id: 'resumen', label: 'Resumen' },
  { id: 'mapa', label: 'Mapa' },
  { id: 'impacto', label: 'Impacto' },
  { id: 'hype', label: 'Hype Cycle' },
  { id: 'detalle', label: 'Detalle' },
  { id: 'metodologia', label: 'Metodología' },
];

@Component({
  selector: 'app-trendmap',
  standalone: true,
  imports: [
    DecimalPipe,
    TrendmapOverviewComponent,
    D3ScatterComponent,
    TrendmapImpactComponent,
    HypeCycleComponent,
    TrendmapDetailComponent,
    TrendmapMethodologyComponent,
    TrendmapSidebarComponent,
  ],
  template: `
    <div class="min-h-screen bg-dark-bg text-dark-text">
      <div class="p-6">
        <div class="mb-6 grid gap-4 xl:grid-cols-[1.5fr_1fr]">
          <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
            <div class="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 class="text-2xl font-semibold">Trend Mapping</h2>
                <p class="mt-2 max-w-3xl text-sm leading-6 text-dark-muted">
                  Snapshot-driven, con scoring interpretable, clusterización híbrida y detalle
                  explicable por cluster.
                </p>
              </div>
              @if (service.data()?.methodology_version) {
                <span class="rounded-full border border-dark-border bg-dark-bg px-3 py-1 text-xs text-dark-muted">
                  {{ service.data()?.methodology_version }}
                </span>
              }
            </div>

            @if (service.data()?.summary?.executive_summary) {
              <p class="mt-4 text-sm leading-6 text-dark-text/90">
                {{ service.data()?.summary?.executive_summary }}
              </p>
            }

            @if (service.data()?.comparative_signals?.summary) {
              <div class="mt-4 rounded-xl border border-dark-border bg-dark-bg/70 px-4 py-3 text-sm text-dark-muted">
                {{ service.data()?.comparative_signals?.summary }}
              </div>
            }
          </section>

          <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
            <h3 class="text-xs font-semibold uppercase tracking-[0.18em] text-dark-muted">
              Filtros activos
            </h3>
            <div class="mt-3 flex flex-wrap gap-2">
              @for (tag of service.activeFilterSummary(); track tag) {
                <span class="rounded-full border border-dark-border bg-dark-bg px-3 py-1 text-xs text-dark-muted">
                  {{ tag }}
                </span>
              }
            </div>
            @if (service.highlightCards().length > 0) {
              <div class="mt-4 space-y-2">
                @for (card of service.highlightCards().slice(0, 3); track card.cluster_id) {
                  <div class="rounded-xl border border-dark-border bg-dark-bg/60 p-3">
                    <p class="text-sm font-medium text-dark-text">{{ card.label }}</p>
                    <p class="mt-1 text-xs text-dark-muted">
                      Impacto {{ card.impact_score | number:'1.0-0' }} · Momentum
                      {{ card.momentum_score | number:'1.0-0' }}
                    </p>
                  </div>
                }
              </div>
            }
          </section>
        </div>

        @if (service.loading()) {
          <p class="text-dark-muted text-sm">Cargando datos de tendencias...</p>
        } @else if (service.error()) {
          <p class="text-red-400 text-sm" role="alert">{{ service.error() }}</p>
        } @else {
          <!-- Tabs -->
          <nav class="flex border-b border-dark-border mb-6" role="tablist">
            @for (tab of tabs; track tab.id) {
              <button
                role="tab"
                [attr.aria-selected]="activeTab() === tab.id"
                [class]="tabClass(tab.id)"
                (click)="activeTab.set(tab.id)"
              >
                {{ tab.label }}
              </button>
            }
          </nav>

          <div class="flex gap-6">
            <!-- Main content -->
            <div class="flex-1 min-w-0">
              @switch (activeTab()) {
                @case ('resumen') {
                  <app-trendmap-overview [data]="service.data()!" />
                }
                @case ('mapa') {
                  <app-d3-scatter
                    [articles]="service.filteredArticles()"
                    [clusters]="service.filteredClusters()"
                    [selectedCluster]="service.selectedCluster()"
                    (clusterSelected)="service.selectCluster($event)"
                  />
                }
                @case ('impacto') {
                  <app-trendmap-impact [clusters]="service.filteredClusters()" />
                }
                @case ('hype') {
                  <app-hype-cycle [clusters]="service.filteredClusters()" />
                }
                @case ('detalle') {
                  <app-trendmap-detail
                    [cluster]="service.selectedCluster()"
                    [articles]="selectedOrFilteredArticles()"
                  />
                }
                @case ('metodologia') {
                  <app-trendmap-methodology
                    [methodology]="service.data()?.methodology ?? null"
                    [qualityChecks]="service.data()?.quality_checks ?? null"
                    [filtersMetadata]="service.data()?.filters_metadata ?? null"
                  />
                }
              }
            </div>

            <!-- Sidebar (visible on mapa and detalle tabs) -->
            @if (showSidebar()) {
              <app-trendmap-sidebar
                [clusters]="service.filteredClusters()"
                [categories]="service.categories()"
                [filtersMetadata]="service.data()?.filters_metadata ?? null"
                [selectedCluster]="service.selectedCluster()"
                [filterCategory]="service.filterCategory()"
                [filterSourceType]="service.filterSourceType()"
                [filterMaturityStage]="service.filterMaturityStage()"
                [filterHypeStage]="service.filterHypeStage()"
                [weakSignalsOnly]="service.weakSignalsOnly()"
                [sortBy]="service.sortBy()"
                [qualityChecks]="service.data()?.quality_checks ?? null"
                (clusterSelected)="service.selectCluster($event)"
                (categoryChanged)="service.setFilterCategory($event)"
                (sourceTypeChanged)="service.setFilterSourceType($event)"
                (maturityStageChanged)="service.setFilterMaturityStage($event)"
                (hypeStageChanged)="service.setFilterHypeStage($event)"
                (weakSignalsChanged)="service.setWeakSignalsOnly($event)"
                (sortChanged)="service.setSortBy($event)"
                (clearRequested)="service.clearFilters()"
              />
            }
          </div>
        }
      </div>
    </div>
  `,
})
export class TrendmapComponent implements OnInit {
  readonly service = inject(TrendmapSignalService);

  readonly tabs = TABS;
  readonly activeTab = signal<TabId>('resumen');

  readonly showSidebar = computed(() => {
    const tab = this.activeTab();
    return tab !== 'metodologia';
  });

  readonly selectedOrFilteredArticles = computed(() => {
    const selected = this.service.selectedClusterArticles();
    return selected.length > 0 ? selected : this.service.filteredArticles();
  });

  ngOnInit(): void {
    this.service.load();
  }

  tabClass(tabId: TabId): string {
    const base = 'px-4 py-2 text-sm font-medium transition-colors cursor-pointer ';
    if (this.activeTab() === tabId) {
      return base + 'text-dark-accent border-b-2 border-dark-accent';
    }
    return base + 'text-dark-muted hover:text-dark-text';
  }
}
