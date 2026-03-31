import { Component, input, output } from '@angular/core';
import { TrendmapCluster } from '../../../../../domain/noticias/models';

@Component({
  selector: 'app-trendmap-sidebar',
  standalone: true,
  template: `
    <aside class="w-80 shrink-0 space-y-4">
      <!-- Category filter -->
      <div class="bg-dark-surface border border-dark-border rounded-lg p-3">
        <label for="sidebar-category" class="text-xs text-dark-muted block mb-1">
          Filtrar por categoría
        </label>
        <select
          id="sidebar-category"
          class="w-full bg-dark-bg border border-dark-border text-dark-text text-sm rounded px-2 py-1.5"
          [value]="filterCategory() ?? ''"
          (change)="onCategoryChange($event)"
        >
          <option value="">Todas</option>
          @for (cat of categories(); track cat) {
            <option [value]="cat">{{ cat }}</option>
          }
        </select>
      </div>

      <!-- Cluster cards -->
      <div class="space-y-2 max-h-[calc(100vh-240px)] overflow-y-auto pr-1">
        @for (cluster of clusters(); track cluster.cluster_id) {
          <button
            class="w-full text-left bg-dark-surface border rounded-lg p-3 transition-all cursor-pointer"
            [class]="cardClass(cluster)"
            (click)="onClusterClick(cluster)"
          >
            <div class="flex justify-between items-start mb-1">
              <h5 class="text-sm font-semibold text-dark-text leading-tight flex-1 mr-2">
                {{ cluster.label }}
              </h5>
              <span [class]="relevanceBadge(cluster.relevance)">
                {{ cluster.relevance }}
              </span>
            </div>

            <div class="flex flex-wrap gap-1 mb-2">
              @for (kw of cluster.keywords.slice(0, 4); track kw) {
                <span class="text-[10px] bg-dark-bg text-dark-muted px-1.5 py-0.5 rounded">
                  {{ kw }}
                </span>
              }
            </div>

            <div class="flex gap-3 text-xs text-dark-muted">
              <span>{{ cluster.item_count }} artículos</span>
              <span>Impacto: {{ cluster.impact_score | number:'1.0-0' }}</span>
            </div>
          </button>
        }

        @if (clusters().length === 0) {
          <p class="text-dark-muted text-sm text-center py-4">
            No hay clusters para esta categoría.
          </p>
        }
      </div>
    </aside>
  `,
})
export class TrendmapSidebarComponent {
  readonly clusters = input<TrendmapCluster[]>([]);
  readonly categories = input<string[]>([]);
  readonly selectedCluster = input<TrendmapCluster | null>(null);
  readonly filterCategory = input<string | null>(null);

  readonly clusterSelected = output<TrendmapCluster | null>();
  readonly categoryChanged = output<string | null>();

  onClusterClick(cluster: TrendmapCluster): void {
    const current = this.selectedCluster();
    this.clusterSelected.emit(
      current?.cluster_id === cluster.cluster_id ? null : cluster,
    );
  }

  onCategoryChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.categoryChanged.emit(value || null);
  }

  cardClass(cluster: TrendmapCluster): string {
    const isSelected = this.selectedCluster()?.cluster_id === cluster.cluster_id;
    if (isSelected) {
      return 'border-dark-accent bg-dark-bg';
    }
    return 'border-dark-border hover:border-dark-muted';
  }

  relevanceBadge(relevance: 'alta' | 'media' | 'baja'): string {
    const base = 'text-[10px] font-medium px-2 py-0.5 rounded-full ';
    switch (relevance) {
      case 'alta':
        return base + 'bg-red-900/40 text-red-400';
      case 'media':
        return base + 'bg-yellow-900/40 text-yellow-400';
      case 'baja':
        return base + 'bg-green-900/40 text-green-400';
    }
  }
}
