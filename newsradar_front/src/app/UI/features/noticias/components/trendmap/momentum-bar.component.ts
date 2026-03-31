import { Component, computed, input } from '@angular/core';
import * as d3 from 'd3';

const BAR_WIDTH = 120;
const BAR_HEIGHT = 10;

@Component({
  selector: 'app-momentum-bar',
  standalone: true,
  template: `
    <div class="flex items-center gap-2"
      [attr.aria-label]="label() ? label() + ': ' + pct() + '%' : 'Momentum: ' + pct() + '%'">
      @if (label()) {
        <span class="text-xs text-gray-500 whitespace-nowrap">{{ label() }}</span>
      }
      <svg [attr.width]="barWidth" [attr.height]="barHeight" role="progressbar"
        [attr.aria-valuenow]="pct()" aria-valuemin="0" aria-valuemax="100">
        <rect x="0" y="0" [attr.width]="barWidth" [attr.height]="barHeight"
          rx="3" fill="#E5E7EB" />
        <rect x="0" y="0" [attr.width]="fillWidth()" [attr.height]="barHeight"
          rx="3" fill="#4B5563" data-testid="momentum-fill" />
      </svg>
      <span class="text-xs font-medium text-gray-500 min-w-[32px] text-right" data-testid="momentum-pct">
        {{ pct() }}%
      </span>
    </div>
  `,
})
export class MomentumBarComponent {
  readonly value = input(0);
  readonly label = input<string | undefined>(undefined);

  readonly barWidth = BAR_WIDTH;
  readonly barHeight = BAR_HEIGHT;

  private readonly scale = d3.scaleLinear().domain([0, 1]).range([0, BAR_WIDTH]).clamp(true);

  readonly pct = computed(() => Math.round(Math.min(1, Math.max(0, this.value())) * 100));
  readonly fillWidth = computed(() => this.scale(Math.min(1, Math.max(0, this.value()))));
}
