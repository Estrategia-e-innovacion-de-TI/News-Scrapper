import { Component, computed, inject, input, output } from '@angular/core';
import { Cluster } from '../../../../../domain/noticias/models';
import { TrendmapService } from '../../../../../domain/noticias/services/trendmap.service';
import { ClusterCardComponent } from './cluster-card.component';

@Component({
  selector: 'app-cluster-list',
  standalone: true,
  imports: [ClusterCardComponent],
  template: `
    <section data-testid="cluster-list">
      <h3 class="text-base font-semibold mb-3">Clusters</h3>

      <div class="mb-4">
        <label for="cluster-category-filter" class="text-sm mr-2">Filtrar por categoría:</label>
        <select id="cluster-category-filter" data-testid="cluster-category-filter"
          [value]="selectedCategory()"
          (change)="categoryChange.emit(asInputValue($event))"
          class="border rounded px-3 py-1.5 text-sm max-w-xs">
          <option value="">Todas</option>
          @for (cat of categories(); track cat) {
            <option [value]="cat">{{ cat }}</option>
          }
        </select>
      </div>

      @if (filteredClusters().length === 0) {
        <p class="text-gray-500 text-sm" data-testid="cluster-empty">No se encontraron clusters para esta categoría.</p>
      } @else {
        @for (cluster of filteredClusters(); track cluster.cluster_id) {
          <app-cluster-card [cluster]="cluster" />
        }
      }
    </section>
  `,
})
export class ClusterListComponent {
  private readonly trendmapService = inject(TrendmapService);

  readonly clusters = input<Cluster[]>([]);
  readonly selectedCategory = input('');
  readonly categoryChange = output<string>();

  readonly categories = computed(() => {
    const cats = new Set(this.clusters().map((c) => c.category));
    return Array.from(cats).sort();
  });

  readonly filteredClusters = computed(() => {
    const cat = this.selectedCategory();
    const all = this.clusters();
    const filtered = cat ? this.trendmapService.filterClustersByCategory(all, cat) : all;
    return this.trendmapService.sortClustersByImpact(filtered);
  });

  asInputValue(event: Event): string {
    return (event.target as HTMLSelectElement).value;
  }
}
