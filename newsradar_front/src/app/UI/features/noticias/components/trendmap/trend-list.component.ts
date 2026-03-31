import { Component, computed, inject, input } from '@angular/core';
import { Trend, HypeStage } from '../../../../../domain/noticias/models';
import { TrendmapService } from '../../../../../domain/noticias/services/trendmap.service';
import { MomentumBarComponent } from './momentum-bar.component';

const DIRECTION_LABELS: Record<Trend['direction'], string> = {
  creciente: '↑ Creciente',
  decreciente: '↓ Decreciente',
  estable: '→ Estable',
};

const STAGE_ORDER: HypeStage[] = [
  'trigger',
  'peak_of_inflated_expectations',
  'trough_of_disillusionment',
  'slope_of_enlightenment',
  'plateau_of_productivity',
];

const STAGE_LABELS: Record<HypeStage, string> = {
  trigger: 'Innovation Trigger',
  peak_of_inflated_expectations: 'Peak of Inflated Expectations',
  trough_of_disillusionment: 'Trough of Disillusionment',
  slope_of_enlightenment: 'Slope of Enlightenment',
  plateau_of_productivity: 'Plateau of Productivity',
};

@Component({
  selector: 'app-trend-list',
  standalone: true,
  imports: [MomentumBarComponent],
  template: `
    <section data-testid="trend-list">
      <h3 class="text-base font-semibold mb-3">Tendencias</h3>

      @if (trends().length === 0) {
        <p class="text-gray-500 text-sm" data-testid="trend-list-empty">No hay tendencias disponibles.</p>
      } @else {
        @for (entry of groupedEntries(); track entry.stage) {
          <div class="mb-4">
            <h4 class="text-sm font-semibold text-gray-700 mb-2">{{ stageLabel(entry.stage) }} ({{ entry.trends.length }})</h4>
            @for (t of entry.trends; track t.trend) {
              <div class="bg-white rounded-lg p-4 mb-2 shadow-sm"
                [style.border-left]="'4px solid ' + directionColor(t.direction)">
                <div class="flex justify-between items-center mb-1">
                  <span class="font-semibold text-sm" data-testid="trend-name">{{ t.trend }}</span>
                  <div class="flex gap-2 items-center">
                    <span class="text-xs bg-gray-100 px-2 py-0.5 rounded" data-testid="trend-category">{{ t.category }}</span>
                    <span class="text-xs font-medium" [style.color]="directionColor(t.direction)" data-testid="trend-direction">
                      {{ directionLabel(t.direction) }}
                    </span>
                  </div>
                </div>
                <div class="mb-1" data-testid="trend-momentum">
                  <app-momentum-bar [value]="t.momentum" label="Momentum" />
                </div>
                <p class="text-xs text-gray-500" data-testid="trend-maturity">Etapa: {{ t.maturity_stage }}</p>
                <p class="text-sm mt-1" data-testid="trend-description">{{ t.description }}</p>
                <p class="text-sm text-gray-500" data-testid="trend-impact">Impacto financiero: {{ t.impact_on_finance }}</p>
              </div>
            }
          </div>
        }
      }
    </section>
  `,
})
export class TrendListComponent {
  private readonly trendmapService = inject(TrendmapService);

  readonly trends = input<Trend[]>([]);

  readonly groupedEntries = computed(() => {
    const grouped = this.trendmapService.groupTrendsByMaturity(this.trends());
    return STAGE_ORDER
      .map((stage) => ({ stage, trends: grouped.get(stage) ?? [] }))
      .filter((e) => e.trends.length > 0);
  });

  directionColor(direction: Trend['direction']): string {
    return this.trendmapService.getDirectionColor(direction);
  }

  directionLabel(direction: Trend['direction']): string {
    return DIRECTION_LABELS[direction];
  }

  stageLabel(stage: HypeStage): string {
    return STAGE_LABELS[stage];
  }
}
