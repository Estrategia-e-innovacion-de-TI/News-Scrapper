import {
  AfterViewInit,
  Component,
  ElementRef,
  effect,
  input,
  viewChild,
} from '@angular/core';
import * as d3 from 'd3';

import {
  DARK_THEME,
  LifecycleStage,
  TrendmapCluster,
} from '../../../../../domain/noticias/models';

const WIDTH = 860;
const HEIGHT = 420;
const MARGIN = { top: 36, right: 28, bottom: 78, left: 30 };

const STAGE_ORDER: LifecycleStage[] = [
  'weak_signal',
  'innovation_trigger',
  'rising_attention',
  'peak_visibility',
  'correction',
  'consolidation',
  'productive_adoption',
];

const STAGE_LABELS: Record<LifecycleStage, string> = {
  weak_signal: 'Weak Signal',
  innovation_trigger: 'Innovation Trigger',
  rising_attention: 'Rising Attention',
  peak_visibility: 'Peak Visibility',
  correction: 'Correction',
  consolidation: 'Consolidation',
  productive_adoption: 'Productive Adoption',
};

const STAGE_X: Record<LifecycleStage, number> = {
  weak_signal: 0.06,
  innovation_trigger: 0.18,
  rising_attention: 0.34,
  peak_visibility: 0.49,
  correction: 0.64,
  consolidation: 0.79,
  productive_adoption: 0.93,
};

const STAGE_Y: Record<LifecycleStage, number> = {
  weak_signal: 0.2,
  innovation_trigger: 0.33,
  rising_attention: 0.62,
  peak_visibility: 0.92,
  correction: 0.24,
  consolidation: 0.58,
  productive_adoption: 0.68,
};

@Component({
  selector: 'app-hype-cycle',
  standalone: true,
  template: `
    <div class="rounded-2xl border border-dark-border bg-dark-surface p-4">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h4 class="text-sm font-semibold text-dark-text">Hype cycle operativo</h4>
          <p class="mt-1 text-xs leading-5 text-dark-muted">
            La etapa no la decide el LLM: sale de madurez, impacto, momentum, novedad e incertidumbre.
          </p>
        </div>
      </div>
      <svg #chart [attr.width]="width" [attr.height]="height"></svg>
    </div>
  `,
})
export class HypeCycleComponent implements AfterViewInit {
  readonly clusters = input<TrendmapCluster[]>([]);
  readonly chartRef = viewChild.required<ElementRef<SVGSVGElement>>('chart');

  readonly width = WIDTH;
  readonly height = HEIGHT;

  private initialized = false;

  constructor() {
    effect(() => {
      if (this.initialized) {
        this.render(this.clusters());
      }
    });
  }

  ngAfterViewInit(): void {
    this.initialized = true;
    this.render(this.clusters());
  }

  private render(clusters: TrendmapCluster[]): void {
    const svg = d3.select(this.chartRef().nativeElement);
    svg.selectAll('*').remove();

    if (clusters.length === 0) {
      return;
    }

    svg
      .append('rect')
      .attr('width', WIDTH)
      .attr('height', HEIGHT)
      .attr('fill', DARK_THEME.bg)
      .attr('rx', 12);

    const innerWidth = WIDTH - MARGIN.left - MARGIN.right;
    const innerHeight = HEIGHT - MARGIN.top - MARGIN.bottom;
    const x = d3.scaleLinear().domain([0, 1]).range([MARGIN.left, MARGIN.left + innerWidth]);
    const y = d3.scaleLinear().domain([0, 1]).range([MARGIN.top + innerHeight, MARGIN.top]);

    const anchors: [number, number][] = STAGE_ORDER.map((stage) => [
      x(STAGE_X[stage]),
      y(STAGE_Y[stage]),
    ]);

    const curve = d3
      .line<[number, number]>()
      .x((point) => point[0])
      .y((point) => point[1])
      .curve(d3.curveBasis);

    svg
      .append('path')
      .datum([[x(0), y(0.16)], ...anchors, [x(1), y(0.7)]] as [number, number][])
      .attr('d', curve)
      .attr('fill', 'none')
      .attr('stroke', '#475569')
      .attr('stroke-width', 2.5)
      .attr('stroke-dasharray', '7,4');

    STAGE_ORDER.forEach((stage) => {
      const stageX = x(STAGE_X[stage]);
      svg
        .append('line')
        .attr('x1', stageX)
        .attr('x2', stageX)
        .attr('y1', MARGIN.top)
        .attr('y2', HEIGHT - MARGIN.bottom)
        .attr('stroke', DARK_THEME.border)
        .attr('stroke-dasharray', '3,6')
        .attr('stroke-opacity', 0.7);

      svg
        .append('text')
        .attr('x', stageX)
        .attr('y', HEIGHT - MARGIN.bottom + 18)
        .attr('text-anchor', 'middle')
        .attr('fill', DARK_THEME.textMuted)
        .attr('font-size', '9px')
        .text(STAGE_LABELS[stage]);
    });

    svg
      .append('text')
      .attr('x', 14)
      .attr('y', HEIGHT / 2)
      .attr('transform', `rotate(-90 14 ${HEIGHT / 2})`)
      .attr('fill', DARK_THEME.textMuted)
      .attr('font-size', '10px')
      .text('Visibilidad / expectativas');

    const radius = d3
      .scaleSqrt()
      .domain([0, d3.max(clusters, (cluster) => cluster.item_count) ?? 1])
      .range([7, 26]);

    const color = d3.scaleOrdinal<string, string>(d3.schemeTableau10);
    const stageCounts = new Map<LifecycleStage, number>();

    clusters.forEach((cluster) => {
      const stage = cluster.hype_stage;
      const currentCount = stageCounts.get(stage) ?? 0;
      stageCounts.set(stage, currentCount + 1);

      const baseX = x(STAGE_X[stage]);
      const baseY = y(STAGE_Y[stage]);
      const jitterX = ((currentCount % 4) - 1.5) * 16;
      const jitterY = Math.floor(currentCount / 4) * 14 - cluster.momentum_score * 0.15;
      const bubbleX = baseX + jitterX;
      const bubbleY = baseY + jitterY;

      const group = svg.append('g');
      group
        .append('circle')
        .attr('cx', bubbleX)
        .attr('cy', bubbleY)
        .attr('r', radius(cluster.item_count))
        .attr('fill', color(cluster.category))
        .attr('fill-opacity', 0.78)
        .attr('stroke', '#e2e8f0')
        .attr('stroke-opacity', 0.12)
        .attr('stroke-width', 1.2);

      group
        .append('title')
        .text(
          `${cluster.label}
Stage: ${cluster.hype_stage.replaceAll('_', ' ')}
Impacto: ${cluster.impact_score.toFixed(1)}
Madurez: ${cluster.maturity_score.toFixed(1)}
Momentum: ${cluster.momentum_score.toFixed(1)}
Incertidumbre: ${cluster.uncertainty_score.toFixed(1)}`,
        );

      group
        .append('text')
        .attr('x', bubbleX)
        .attr('y', bubbleY - radius(cluster.item_count) - 8)
        .attr('text-anchor', 'middle')
        .attr('fill', DARK_THEME.text)
        .attr('font-size', '8px')
        .text(cluster.label.length > 20 ? `${cluster.label.slice(0, 20)}...` : cluster.label);
    });
  }
}
