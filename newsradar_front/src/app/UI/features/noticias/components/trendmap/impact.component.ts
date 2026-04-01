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

const WIDTH = 820;
const HEIGHT = 520;
const MARGIN = { top: 28, right: 28, bottom: 56, left: 64 };

const STAGE_COLORS: Record<LifecycleStage, string> = {
  weak_signal: '#f59e0b',
  innovation_trigger: '#38bdf8',
  rising_attention: '#60a5fa',
  peak_visibility: '#f97316',
  correction: '#fb7185',
  consolidation: '#34d399',
  productive_adoption: '#10b981',
};

@Component({
  selector: 'app-trendmap-impact',
  standalone: true,
  template: `
    <div class="rounded-2xl border border-dark-border bg-dark-surface p-4">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h4 class="text-sm font-semibold text-dark-text">Impacto vs madurez</h4>
          <p class="mt-1 text-xs leading-5 text-dark-muted">
            Burbujas por cluster con tamano segun volumen y color segun hype stage.
          </p>
        </div>
      </div>
      <svg #chart [attr.width]="width" [attr.height]="height"></svg>
    </div>
  `,
})
export class TrendmapImpactComponent implements AfterViewInit {
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

    const x = d3.scaleLinear().domain([0, 100]).range([MARGIN.left, WIDTH - MARGIN.right]);
    const y = d3.scaleLinear().domain([0, 100]).range([HEIGHT - MARGIN.bottom, MARGIN.top]);
    const r = d3
      .scaleSqrt()
      .domain([0, d3.max(clusters, (cluster) => cluster.item_count) ?? 1])
      .range([8, 36]);

    const innerWidth = WIDTH - MARGIN.left - MARGIN.right;
    const innerHeight = HEIGHT - MARGIN.top - MARGIN.bottom;
    const quadrantX = x(60);
    const quadrantY = y(60);

    svg
      .append('rect')
      .attr('width', WIDTH)
      .attr('height', HEIGHT)
      .attr('fill', DARK_THEME.bg)
      .attr('rx', 12);

    svg
      .append('rect')
      .attr('x', MARGIN.left)
      .attr('y', MARGIN.top)
      .attr('width', quadrantX - MARGIN.left)
      .attr('height', quadrantY - MARGIN.top)
      .attr('fill', '#132033');

    svg
      .append('rect')
      .attr('x', quadrantX)
      .attr('y', MARGIN.top)
      .attr('width', MARGIN.left + innerWidth - quadrantX)
      .attr('height', quadrantY - MARGIN.top)
      .attr('fill', '#1a2b3a');

    svg
      .append('rect')
      .attr('x', MARGIN.left)
      .attr('y', quadrantY)
      .attr('width', quadrantX - MARGIN.left)
      .attr('height', MARGIN.top + innerHeight - quadrantY)
      .attr('fill', '#101e2e');

    svg
      .append('rect')
      .attr('x', quadrantX)
      .attr('y', quadrantY)
      .attr('width', MARGIN.left + innerWidth - quadrantX)
      .attr('height', MARGIN.top + innerHeight - quadrantY)
      .attr('fill', '#18272f');

    svg
      .append('g')
      .selectAll('line.grid-x')
      .data([20, 40, 60, 80])
      .join('line')
      .attr('x1', (value) => x(value))
      .attr('x2', (value) => x(value))
      .attr('y1', MARGIN.top)
      .attr('y2', HEIGHT - MARGIN.bottom)
      .attr('stroke', DARK_THEME.border)
      .attr('stroke-dasharray', '4,6')
      .attr('stroke-opacity', 0.6);

    svg
      .append('g')
      .selectAll('line.grid-y')
      .data([20, 40, 60, 80])
      .join('line')
      .attr('x1', MARGIN.left)
      .attr('x2', WIDTH - MARGIN.right)
      .attr('y1', (value) => y(value))
      .attr('y2', (value) => y(value))
      .attr('stroke', DARK_THEME.border)
      .attr('stroke-dasharray', '4,6')
      .attr('stroke-opacity', 0.6);

    const xAxis = svg
      .append('g')
      .attr('transform', `translate(0,${HEIGHT - MARGIN.bottom})`)
      .call(d3.axisBottom(x).ticks(5));

    xAxis.selectAll('text').attr('fill', DARK_THEME.textMuted);
    xAxis.selectAll('.domain, .tick line').attr('stroke', DARK_THEME.border);

    const yAxis = svg
      .append('g')
      .attr('transform', `translate(${MARGIN.left},0)`)
      .call(d3.axisLeft(y).ticks(5));

    yAxis.selectAll('text').attr('fill', DARK_THEME.textMuted);
    yAxis.selectAll('.domain, .tick line').attr('stroke', DARK_THEME.border);

    svg
      .append('text')
      .attr('x', WIDTH / 2)
      .attr('y', HEIGHT - 12)
      .attr('text-anchor', 'middle')
      .attr('fill', DARK_THEME.textMuted)
      .attr('font-size', '11px')
      .text('Impacto potencial');

    svg
      .append('text')
      .attr('transform', 'rotate(-90)')
      .attr('x', -HEIGHT / 2)
      .attr('y', 18)
      .attr('text-anchor', 'middle')
      .attr('fill', DARK_THEME.textMuted)
      .attr('font-size', '11px')
      .text('Madurez / recurrencia');

    this.addQuadrantLabel(svg, MARGIN.left + 18, MARGIN.top + 22, 'Explorar', 'alto potencial, baja madurez');
    this.addQuadrantLabel(svg, quadrantX + 18, MARGIN.top + 22, 'Escalar', 'alto potencial, alta madurez');
    this.addQuadrantLabel(svg, MARGIN.left + 18, quadrantY + 22, 'Observar', 'baja madurez y bajo impacto');
    this.addQuadrantLabel(svg, quadrantX + 18, quadrantY + 22, 'Operar', 'maduro pero con foco tactico');

    const bubbles = svg
      .append('g')
      .selectAll('g.cluster')
      .data(clusters)
      .join('g')
      .attr('class', 'cluster');

    bubbles
      .append('circle')
      .attr('cx', (cluster) => x(cluster.impact_score))
      .attr('cy', (cluster) => y(cluster.maturity_score))
      .attr('r', (cluster) => r(cluster.item_count))
      .attr('fill', (cluster) => STAGE_COLORS[cluster.hype_stage])
      .attr('fill-opacity', 0.75)
      .attr('stroke', '#e2e8f0')
      .attr('stroke-opacity', 0.15)
      .attr('stroke-width', 1.2);

    bubbles
      .append('title')
      .text(
        (cluster) =>
          `${cluster.label}
Impacto: ${cluster.impact_score.toFixed(1)}
Madurez: ${cluster.maturity_score.toFixed(1)}
Momentum: ${cluster.momentum_score.toFixed(1)}
Novedad: ${cluster.novelty_score.toFixed(1)}
Docs: ${cluster.item_count}
Stage: ${cluster.hype_stage.replaceAll('_', ' ')}`,
      );

    bubbles
      .filter((cluster) => r(cluster.item_count) >= 14)
      .append('text')
      .attr('x', (cluster) => x(cluster.impact_score))
      .attr('y', (cluster) => y(cluster.maturity_score))
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'central')
      .attr('fill', DARK_THEME.text)
      .attr('font-size', '9px')
      .attr('pointer-events', 'none')
      .text((cluster) =>
        cluster.label.length > 16 ? `${cluster.label.slice(0, 16)}...` : cluster.label,
      );
  }

  private addQuadrantLabel(
    svg: d3.Selection<SVGSVGElement, unknown, null, undefined>,
    xValue: number,
    yValue: number,
    title: string,
    subtitle: string,
  ): void {
    svg
      .append('text')
      .attr('x', xValue)
      .attr('y', yValue)
      .attr('fill', DARK_THEME.text)
      .attr('font-size', '12px')
      .attr('font-weight', '600')
      .text(title);

    svg
      .append('text')
      .attr('x', xValue)
      .attr('y', yValue + 16)
      .attr('fill', DARK_THEME.textMuted)
      .attr('font-size', '10px')
      .text(subtitle);
  }
}
