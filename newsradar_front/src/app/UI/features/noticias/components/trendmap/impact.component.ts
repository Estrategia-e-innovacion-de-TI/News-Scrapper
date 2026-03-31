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
const HEIGHT = 500;
const MARGIN = { top: 30, right: 30, bottom: 50, left: 60 };

@Component({
  selector: 'app-trendmap-impact',
  standalone: true,
  template: `
    <div class="bg-dark-surface border border-dark-border rounded-lg p-4">
      <h4 class="text-sm font-semibold text-dark-text mb-2">Impacto vs Madurez</h4>
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

    if (clusters.length === 0) return;

    // Background
    svg
      .append('rect')
      .attr('width', WIDTH)
      .attr('height', HEIGHT)
      .attr('fill', DARK_THEME.bg)
      .attr('rx', 8);

    const innerW = WIDTH - MARGIN.left - MARGIN.right;
    const innerH = HEIGHT - MARGIN.top - MARGIN.bottom;

    const x = d3
      .scaleLinear()
      .domain([0, d3.max(clusters, (d) => d.impact_score) ?? 100])
      .nice()
      .range([MARGIN.left, MARGIN.left + innerW]);

    const y = d3
      .scaleLinear()
      .domain([0, 1])
      .range([MARGIN.top + innerH, MARGIN.top]);

    const r = d3
      .scaleSqrt()
      .domain([0, d3.max(clusters, (d) => d.item_count) ?? 1])
      .range([6, 40]);

    const color = d3.scaleOrdinal(d3.schemeTableau10);

    // X axis
    const xAxis = svg
      .append('g')
      .attr('transform', `translate(0,${MARGIN.top + innerH})`)
      .call(d3.axisBottom(x).ticks(6));

    xAxis.selectAll('text').attr('fill', DARK_THEME.textMuted);
    xAxis.selectAll('.domain, .tick line').attr('stroke', DARK_THEME.border);

    svg
      .append('text')
      .attr('x', MARGIN.left + innerW / 2)
      .attr('y', HEIGHT - 8)
      .attr('text-anchor', 'middle')
      .attr('fill', DARK_THEME.textMuted)
      .attr('font-size', '11px')
      .text('Impact Score');

    // Y axis
    const yAxis = svg
      .append('g')
      .attr('transform', `translate(${MARGIN.left},0)`)
      .call(d3.axisLeft(y).ticks(5).tickFormat(d3.format('.1f')));

    yAxis.selectAll('text').attr('fill', DARK_THEME.textMuted);
    yAxis.selectAll('.domain, .tick line').attr('stroke', DARK_THEME.border);

    svg
      .append('text')
      .attr('transform', 'rotate(-90)')
      .attr('x', -(MARGIN.top + innerH / 2))
      .attr('y', 14)
      .attr('text-anchor', 'middle')
      .attr('fill', DARK_THEME.textMuted)
      .attr('font-size', '11px')
      .text('Madurez (horizon_score)');

    // Tooltip
    const tooltip = d3
      .select('body')
      .append('div')
      .style('position', 'absolute')
      .style('background', DARK_THEME.surface)
      .style('border', `1px solid ${DARK_THEME.border}`)
      .style('color', DARK_THEME.text)
      .style('padding', '8px 12px')
      .style('border-radius', '6px')
      .style('font-size', '12px')
      .style('pointer-events', 'none')
      .style('opacity', 0)
      .style('z-index', '1000');

    // Bubbles
    svg
      .selectAll('circle.bubble')
      .data(clusters)
      .join('circle')
      .attr('class', 'bubble')
      .attr('cx', (d) => x(d.impact_score))
      .attr('cy', (d) => y(d.horizon_score))
      .attr('r', (d) => r(d.item_count))
      .attr('fill', (d) => color(d.category))
      .attr('fill-opacity', 0.6)
      .attr('stroke', (d) => color(d.category))
      .attr('stroke-width', 1.5)
      .on('mouseenter', (event: MouseEvent, d: TrendmapCluster) => {
        tooltip
          .style('opacity', 1)
          .html(
            `<strong>${d.label}</strong><br/>` +
            `Categoría: ${d.category}<br/>` +
            `Impacto: ${d.impact_score.toFixed(1)}<br/>` +
            `Madurez: ${d.horizon_score.toFixed(2)}<br/>` +
            `Artículos: ${d.item_count}<br/>` +
            `Keywords: ${d.keywords.slice(0, 4).join(', ')}`,
          );
      })
      .on('mousemove', (event: MouseEvent) => {
        tooltip
          .style('left', event.pageX + 12 + 'px')
          .style('top', event.pageY - 10 + 'px');
      })
      .on('mouseleave', () => {
        tooltip.style('opacity', 0);
      });

    // Labels for larger bubbles
    svg
      .selectAll('text.bubble-label')
      .data(clusters.filter((d) => r(d.item_count) > 15))
      .join('text')
      .attr('class', 'bubble-label')
      .attr('x', (d) => x(d.impact_score))
      .attr('y', (d) => y(d.horizon_score))
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'central')
      .attr('font-size', '9px')
      .attr('fill', DARK_THEME.text)
      .attr('pointer-events', 'none')
      .text((d) => d.label.length > 12 ? d.label.slice(0, 12) + '…' : d.label);
  }
}
