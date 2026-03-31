import { Component, inject, OnInit, signal, computed } from '@angular/core';
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
        <h2 class="text-xl font-semibold mb-6">Trend Mapping</h2>

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
                    [articles]="selectedOrFilteredArticles()"
                  />
                }
                @case ('metodologia') {
                  <app-trendmap-methodology />
                }
              }
            </div>

            <!-- Sidebar (visible on mapa and detalle tabs) -->
            @if (showSidebar()) {
              <app-trendmap-sidebar
                [clusters]="service.filteredClusters()"
                [categories]="service.categories()"
                [selectedCluster]="service.selectedCluster()"
                [filterCategory]="service.filterCategory()"
                (clusterSelected)="service.selectCluster($event)"
                (categoryChanged)="service.setFilterCategory($event)"
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
    return tab === 'mapa' || tab === 'detalle';
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
