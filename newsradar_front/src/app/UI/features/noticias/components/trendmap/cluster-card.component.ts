import { Component, input } from '@angular/core';
import { Cluster } from '../../../../../domain/noticias/models';

@Component({
  selector: 'app-cluster-card',
  standalone: true,
  template: `
    <div class="bg-white rounded-lg p-4 mb-3 shadow-sm border border-transparent hover:shadow-md transition-shadow"
      [attr.data-testid]="'cluster-card-' + cluster().cluster_id">

      <div class="flex justify-between items-center">
        <h4 class="font-semibold text-sm" data-testid="cluster-label">{{ cluster().label }}</h4>
        <span class="text-xs bg-yellow-400 text-black px-2 py-0.5 rounded" data-testid="cluster-category">
          {{ cluster().category }}
        </span>
      </div>

      <p class="text-sm text-gray-600 my-2" data-testid="cluster-summary">{{ cluster().summary }}</p>

      <div class="flex flex-wrap gap-1 mb-2" data-testid="cluster-keywords">
        @for (kw of cluster().keywords; track kw) {
          <span class="text-xs bg-gray-100 px-2 py-0.5 rounded">{{ kw }}</span>
        }
      </div>

      <div class="flex gap-4 text-xs text-gray-500">
        <span data-testid="cluster-item-count">Artículos: {{ cluster().item_count }}</span>
        <span data-testid="cluster-impact-score">Impacto: {{ cluster().impact_score }}</span>
        <span data-testid="cluster-horizon-score">Horizonte: {{ cluster().horizon_score }}</span>
      </div>
    </div>
  `,
})
export class ClusterCardComponent {
  readonly cluster = input.required<Cluster>();
}
