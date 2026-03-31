import {
  Component,
  ElementRef,
  input,
  effect,
  viewChild,
  AfterViewInit,
} from '@angular/core';
import { TrendmapData, DARK_THEME } from '../../../../../domain/noticias/models';
import * as d3 from 'd3';

interface KpiCard {
  label: string;
  value: number | string;
}

@Component({
  selector: 'app-trendmap-overview',
  standalone: true,
  template: `
    <div class="space-y-6">
      <!-- KPI Cards -->
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        @for (kpi of kpis(); track kpi.label) {
          <div class="bg-dark-surface border border-dark-border rounded-lg p-4">
            <p class="text-dark-muted text-xs uppercase tracking-wide">{{ kpi.label }}</p>
            <p class="text-2xl font-bold text-dark-text mt-1">{{ kpi.value }}</p>
          </div>
        }
      </div>

      <!-- Charts -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="bg-dark-surface border border-dark-border rounded-lg p-4">
          <h4 class="text-sm font-semibold text-dark-text mb-3">Distribución por Categoría</h4>
          <svg #categoryChart></svg>
        </div>
        <div class="bg-dark-surface border border-dark-border rounded-lg p-4">
          <h4 class="text-sm font-semibold text-dark-text mb-3">Timeline de Tendencias</h4>
          <svg #timelineChart></svg>
        </div>
      </div>
    </div>
  `,
})
export class TrendmapOverviewComponent implements AfterViewInit {
  readonly data = input.required<TrendmapData>();
  readonly categoryChartRef = viewChild.required<ElementRef<SVGSVGElement>>('categoryChart');
  readonly timelineChartRef = viewChild.required<ElementRef<SVGSVGElement>>('timelineChart');

  private initialized = false;

  constructor() {
    effect(() => {
      const d = this.data();
      if (this.initialized && d) {
        this.renderCategoryChart(d);
        this.renderTimelineChart(d);
      }
    });
  }

  kpis = () => {
    const d = this.data();
    if (!d) return [];
    const cards: KpiCard[] = [
      { label: 'Noticias', value: d.meta.total_articles },
      { label: 'Papers', value: d.meta.total_papers },
      { label: 'Filtrados', value: d.meta.total_filtered },
      { label: 'Clusters', value: d.meta.total_clusters },
      { label: 'Categorías', value: d.meta.total_categories },
      { label: 'Silhouette', value: d.meta.silhouette_score.toFixed(3) },
    ];
    return cards;
  };

  ngAfterViewInit(): void {
    this.initialized = true;
    const d = this.data();
    if (d) {
      this.renderCategoryChart(d);
      this.renderTimelineChart(d);
    }
  }

  private renderCategoryChart(data: TrendmapData): void {
    const svg = d3.select(this.categoryChartRef().nativeElement);
    svg.selectAll('*').remove();

    const width = 500;
    const height = 300;
    const margin = { top: 10, right: 20, bottom: 60, left: 50 };

    svg.attr('width', width).attr('height', height);

    // Count articles per category
    const catCounts = d3.rollup(
      data.clusters,
      (v) => d3.sum(v, (c) => c.item_count),
      (c) => c.category,
    );
    const entries = Array.from(catCounts, ([cat, count]) => ({ cat, count }))
      .sort((a, b) => b.count - a.count);

    if (entries.length === 0) return;

    const x = d3
      .scaleBand()
      .domain(entries.map((e) => e.cat))
      .range([margin.left, width - margin.right])
      .padding(0.3);

    const y = d3
      .scaleLinear()
      .domain([0, d3.max(entries, (e) => e.count) ?? 0])
      .nice()
      .range([height - margin.bottom, margin.top]);

    const color = d3.scaleOrdinal(d3.schemeTableau10);

    // Bars
    svg
      .selectAll('rect')
      .data(entries)
      .join('rect')
      .attr('x', (d) => x(d.cat)!)
      .attr('y', (d) => y(d.count))
      .attr('width', x.bandwidth())
      .attr('height', (d) => y(0) - y(d.count))
      .attr('fill', (d) => color(d.cat))
      .attr('rx', 3);

    // X axis
    svg
      .append('g')
      .attr('transform', `translate(0,${height - margin.bottom})`)
      .call(d3.axisBottom(x))
      .selectAll('text')
      .attr('fill', DARK_THEME.textMuted)
      .attr('font-size', '10px')
      .attr('transform', 'rotate(-30)')
      .attr('text-anchor', 'end');

    svg.selectAll('.domain, .tick line').attr('stroke', DARK_THEME.border);

    // Y axis
    svg
      .append('g')
      .attr('transform', `translate(${margin.left},0)`)
      .call(d3.axisLeft(y).ticks(5))
      .selectAll('text')
      .attr('fill', DARK_THEME.textMuted);

    svg.selectAll('.domain, .tick line').attr('stroke', DARK_THEME.border);
  }

  private renderTimelineChart(data: TrendmapData): void {
    const svg = d3.select(this.timelineChartRef().nativeElement);
    svg.selectAll('*').remove();

    const width = 500;
    const height = 300;
    const margin = { top: 10, right: 20, bottom: 40, left: 50 };

    svg.attr('width', width).attr('height', height);

    const trends = data.trends;
    if (!trends || trends.length === 0) return;

    // Group by date
    const dateCounts = d3.rollup(
      trends,
      (v) => d3.sum(v, (t) => t.count),
      (t) => t.date,
    );
    const entries = Array.from(dateCounts, ([date, count]) => ({ date, count }))
      .sort((a, b) => a.date.localeCompare(b.date));

    if (entries.length === 0) return;

    const x = d3
      .scaleBand()
      .domain(entries.map((e) => e.date))
      .range([margin.left, width - margin.right])
      .padding(0.2);

    const y = d3
      .scaleLinear()
      .domain([0, d3.max(entries, (e) => e.count) ?? 0])
      .nice()
      .range([height - margin.bottom, margin.top]);

    // Area/line
    const line = d3
      .line<{ date: string; count: number }>()
      .x((d) => x(d.date)! + x.bandwidth() / 2)
      .y((d) => y(d.count))
      .curve(d3.curveMonotoneX);

    svg
      .append('path')
      .datum(entries)
      .attr('d', line)
      .attr('fill', 'none')
      .attr('stroke', DARK_THEME.accent)
      .attr('stroke-width', 2);

    // Dots
    svg
      .selectAll('circle')
      .data(entries)
      .join('circle')
      .attr('cx', (d) => x(d.date)! + x.bandwidth() / 2)
      .attr('cy', (d) => y(d.count))
      .attr('r', 3)
      .attr('fill', DARK_THEME.accent);

    // X axis
    svg
      .append('g')
      .attr('transform', `translate(0,${height - margin.bottom})`)
      .call(d3.axisBottom(x).tickValues(x.domain().filter((_, i) => i % Math.ceil(entries.length / 6) === 0)))
      .selectAll('text')
      .attr('fill', DARK_THEME.textMuted)
      .attr('font-size', '10px');

    svg.selectAll('.domain, .tick line').attr('stroke', DARK_THEME.border);

    // Y axis
    svg
      .append('g')
      .attr('transform', `translate(${margin.left},0)`)
      .call(d3.axisLeft(y).ticks(5))
      .selectAll('text')
      .attr('fill', DARK_THEME.textMuted);
  }
}
