import {
  Component,
  ElementRef,
  input,
  effect,
  viewChild,
  AfterViewInit,
} from '@angular/core';
import { TrendmapCluster, DARK_THEME } from '../../../../../domain/noticias/models';
import * as d3 from 'd3';

const WIDTH = 800;
const HEIGHT = 400;
const MARGIN = { top: 30, right: 30, bottom: 60, left: 40 };

type GartnerStage =
  | 'trigger'
  | 'peak_of_inflated_expectations'
  | 'trough_of_disillusionment'
  | 'slope_of_enlightenment'
  | 'plateau_of_productivity';

const STAGE_ORDER: GartnerStage[] = [
  'trigger',
  'peak_of_inflated_expectations',
  'trough_of_disillusionment',
  'slope_of_enlightenment',
  'plateau_of_productivity',
];

const STAGE_X: Record<GartnerStage, number> = {
  trigger: 0.08,
  peak_of_inflated_expectations: 0.28,
  trough_of_disillusionment: 0.50,
  slope_of_enlightenment: 0.72,
  plateau_of_productivity: 0.92,
};

const STAGE_Y: Record<GartnerStage, number> = {
  trigger: 0.30,
  peak_of_inflated_expectations: 0.92,
  trough_of_disillusionment: 0.12,
  slope_of_enlightenment: 0.55,
  plateau_of_productivity: 0.65,
};

const STAGE_LABELS: Record<GartnerStage, string> = {
  trigger: 'Innovation\nTrigger',
  peak_of_inflated_expectations: 'Peak of Inflated\nExpectations',
  trough_of_disillusionment: 'Trough of\nDisillusionment',
  slope_of_enlightenment: 'Slope of\nEnlightenment',
  plateau_of_productivity: 'Plateau of\nProductivity',
};

@Component({
  selector: 'app-hype-cycle',
  standalone: true,
  template: `
    <div class="bg-dark-surface border border-dark-border rounded-lg p-4">
      <h4 class="text-sm font-semibold text-dark-text mb-2">Ciclo de Hype (Gartner)</h4>
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
      const data = this.clusters();
      if (this.initialized) {
        this.render(data);
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

    // Background
    svg
      .append('rect')
      .attr('width', WIDTH)
      .attr('height', HEIGHT)
      .attr('fill', DARK_THEME.bg)
      .attr('rx', 8);

    const innerW = WIDTH - MARGIN.left - MARGIN.right;
    const innerH = HEIGHT - MARGIN.top - MARGIN.bottom;

    const x = d3.scaleLinear().domain([0, 1]).range([MARGIN.left, MARGIN.left + innerW]);
    const y = d3.scaleLinear().domain([0, 1]).range([MARGIN.top + innerH, MARGIN.top]);

    // Draw hype curve using basis interpolation
    const curvePoints: [number, number][] = STAGE_ORDER.map((s) => [
      x(STAGE_X[s]),
      y(STAGE_Y[s]),
    ]);

    // Add extra control points for smoother curve
    const extendedPoints: [number, number][] = [
      [x(0), y(0.15)],
      ...curvePoints,
      [x(1), y(0.65)],
    ];

    const line = d3
      .line<[number, number]>()
      .x((d) => d[0])
      .y((d) => d[1])
      .curve(d3.curveBasis);

    svg
      .append('path')
      .datum(extendedPoints)
      .attr('d', line)
      .attr('fill', 'none')
      .attr('stroke', DARK_THEME.border)
      .attr('stroke-width', 2.5)
      .attr('stroke-dasharray', '8,4');

    // Stage labels on X axis
    STAGE_ORDER.forEach((stage) => {
      const lines = STAGE_LABELS[stage].split('\n');
      const textEl = svg
        .append('text')
        .attr('x', x(STAGE_X[stage]))
        .attr('text-anchor', 'middle')
        .attr('font-size', '9px')
        .attr('fill', DARK_THEME.textMuted);

      lines.forEach((line, i) => {
        textEl
          .append('tspan')
          .attr('x', x(STAGE_X[stage]))
          .attr('y', MARGIN.top + innerH + 18 + i * 12)
          .text(line);
      });
    });

    // Stage vertical guides
    STAGE_ORDER.forEach((stage) => {
      svg
        .append('line')
        .attr('x1', x(STAGE_X[stage]))
        .attr('x2', x(STAGE_X[stage]))
        .attr('y1', MARGIN.top)
        .attr('y2', MARGIN.top + innerH)
        .attr('stroke', DARK_THEME.border)
        .attr('stroke-width', 0.5)
        .attr('stroke-dasharray', '3,3');
    });

    const color = d3.scaleOrdinal(d3.schemeTableau10);

    // Scatter clusters on the curve by maturity_stage
    const stageCount = new Map<string, number>();

    clusters.forEach((cluster) => {
      const stage = cluster.maturity_stage as GartnerStage;
      if (!STAGE_X[stage]) return;

      const count = stageCount.get(stage) ?? 0;
      stageCount.set(stage, count + 1);

      const jitterX = (count % 3 - 1) * 18;
      const jitterY = Math.floor(count / 3) * 18;

      const cx = x(STAGE_X[stage]) + jitterX;
      const cy = y(STAGE_Y[stage]) + jitterY;

      svg
        .append('circle')
        .attr('cx', cx)
        .attr('cy', cy)
        .attr('r', 6)
        .attr('fill', color(cluster.category))
        .attr('stroke', DARK_THEME.surface)
        .attr('stroke-width', 1.5)
        .attr('opacity', 0.9);

      // Label
      svg
        .append('text')
        .attr('x', cx)
        .attr('y', cy - 10)
        .attr('text-anchor', 'middle')
        .attr('font-size', '8px')
        .attr('fill', DARK_THEME.text)
        .text(
          cluster.label.length > 18
            ? cluster.label.slice(0, 18) + '…'
            : cluster.label,
        );
    });

    // Y axis label
    svg
      .append('text')
      .attr('transform', 'rotate(-90)')
      .attr('x', -(MARGIN.top + innerH / 2))
      .attr('y', 12)
      .attr('text-anchor', 'middle')
      .attr('fill', DARK_THEME.textMuted)
      .attr('font-size', '10px')
      .text('Expectativas');
  }
}
