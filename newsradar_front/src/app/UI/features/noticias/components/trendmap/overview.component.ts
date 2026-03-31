import {
  AfterViewInit,
  Component,
  ElementRef,
  effect,
  input,
  viewChild,
} from '@angular/core';
import * as d3 from 'd3';

import { DARK_THEME, TrendmapData } from '../../../../../domain/noticias/models';

interface KpiCard {
  label: string;
  value: number | string;
}

@Component({
  selector: 'app-trendmap-overview',
  standalone: true,
  template: `
    <div class="space-y-6">
      <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
        @for (kpi of kpis(); track kpi.label) {
          <div class="bg-dark-surface border border-dark-border rounded-lg p-4">
            <p class="text-dark-muted text-xs uppercase tracking-wide">{{ kpi.label }}</p>
            <p class="text-2xl font-bold text-dark-text mt-1">{{ kpi.value }}</p>
          </div>
        }
      </div>

      @if (data().summary?.executive_summary) {
        <section class="bg-dark-surface border border-dark-border rounded-lg p-5">
          <h4 class="text-sm font-semibold text-dark-text mb-3">Resumen Ejecutivo</h4>
          <p class="text-sm leading-6 text-dark-text/90">
            {{ data().summary?.executive_summary }}
          </p>
          @if (headlineTags().length > 0) {
            <div class="mt-4 flex flex-wrap gap-2">
              @for (tag of headlineTags(); track tag) {
                <span class="text-xs bg-dark-bg border border-dark-border text-dark-muted px-2 py-1 rounded-full">
                  {{ tag }}
                </span>
              }
            </div>
          }
        </section>
      }

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

      <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <section class="bg-dark-surface border border-dark-border rounded-lg p-4">
          <h4 class="text-sm font-semibold text-dark-text mb-3">Insights</h4>
          @if (data().insights.length === 0) {
            <p class="text-sm text-dark-muted">No hay insights disponibles.</p>
          } @else {
            <ul class="space-y-2">
              @for (item of data().insights; track item) {
                <li class="text-sm text-dark-text/90 leading-6 border-l-2 border-dark-accent pl-3">
                  {{ item }}
                </li>
              }
            </ul>
          }
        </section>

        <section class="bg-dark-surface border border-dark-border rounded-lg p-4">
          <h4 class="text-sm font-semibold text-dark-text mb-3">Recomendaciones</h4>
          @if (data().recommendations.length === 0) {
            <p class="text-sm text-dark-muted">No hay recomendaciones disponibles.</p>
          } @else {
            <ul class="space-y-2">
              @for (item of data().recommendations; track item) {
                <li class="text-sm text-dark-text/90 leading-6 border-l-2 border-emerald-500 pl-3">
                  {{ item }}
                </li>
              }
            </ul>
          }
        </section>

        <section class="bg-dark-surface border border-dark-border rounded-lg p-4">
          <h4 class="text-sm font-semibold text-dark-text mb-3">Señales</h4>
          @if (data().risk_signals.length === 0) {
            <p class="text-sm text-dark-muted">No se detectaron señales destacadas.</p>
          } @else {
            <div class="space-y-3">
              @for (signal of data().risk_signals; track signal.type + signal.description) {
                <div class="border border-dark-border rounded-lg p-3 bg-dark-bg/50">
                  <div class="flex items-center justify-between gap-3 mb-1">
                    <span class="text-sm font-medium text-dark-text">{{ signal.type }}</span>
                    <span [class]="severityBadge(signal.severity)">
                      {{ signal.severity }}
                    </span>
                  </div>
                  <p class="text-sm text-dark-text/85 leading-5">{{ signal.description }}</p>
                </div>
              }
            </div>
          }
        </section>
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
      const snapshot = this.data();
      if (this.initialized && snapshot) {
        this.renderCategoryChart(snapshot);
        this.renderTimelineChart(snapshot);
      }
    });
  }

  kpis = () => {
    const snapshot = this.data();
    if (!snapshot) return [];
    const cards: KpiCard[] = [
      { label: 'Noticias', value: snapshot.meta.total_articles },
      { label: 'Papers', value: snapshot.meta.total_papers },
      { label: 'Filtrados', value: snapshot.meta.total_filtered },
      { label: 'Clusters', value: snapshot.meta.total_clusters },
      { label: 'Agrupados', value: snapshot.summary?.clustered_documents ?? 'N/D' },
      { label: 'Sin Cluster', value: snapshot.summary?.unclustered_documents ?? 'N/D' },
      { label: 'Categorías', value: snapshot.meta.total_categories },
      { label: 'Silhouette', value: snapshot.meta.silhouette_score.toFixed(3) },
    ];
    return cards;
  };

  headlineTags = () => {
    const snapshot = this.data();
    if (!snapshot?.summary) return [];
    return [
      ...(snapshot.summary.dominant_topics ?? []),
      ...(snapshot.summary.emerging_topics ?? []),
      ...(snapshot.summary.consolidating_topics ?? []),
    ].slice(0, 6);
  };

  ngAfterViewInit(): void {
    this.initialized = true;
    const snapshot = this.data();
    if (snapshot) {
      this.renderCategoryChart(snapshot);
      this.renderTimelineChart(snapshot);
    }
  }

  private renderCategoryChart(data: TrendmapData): void {
    const svg = d3.select(this.categoryChartRef().nativeElement);
    svg.selectAll('*').remove();

    const width = 500;
    const height = 300;
    const margin = { top: 10, right: 20, bottom: 60, left: 50 };

    svg.attr('width', width).attr('height', height);

    const catCounts = d3.rollup(
      data.clusters,
      (items) => d3.sum(items, (cluster) => cluster.item_count),
      (cluster) => cluster.category,
    );
    const entries = Array.from(catCounts, ([cat, count]) => ({ cat, count })).sort(
      (a, b) => b.count - a.count,
    );

    if (entries.length === 0) return;

    const x = d3
      .scaleBand()
      .domain(entries.map((entry) => entry.cat))
      .range([margin.left, width - margin.right])
      .padding(0.3);

    const y = d3
      .scaleLinear()
      .domain([0, d3.max(entries, (entry) => entry.count) ?? 0])
      .nice()
      .range([height - margin.bottom, margin.top]);

    const color = d3.scaleOrdinal(d3.schemeTableau10);

    svg
      .selectAll('rect')
      .data(entries)
      .join('rect')
      .attr('x', (entry) => x(entry.cat)!)
      .attr('y', (entry) => y(entry.count))
      .attr('width', x.bandwidth())
      .attr('height', (entry) => y(0) - y(entry.count))
      .attr('fill', (entry) => color(entry.cat))
      .attr('rx', 3);

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

    const dateCounts = d3.rollup(
      trends,
      (items) => d3.sum(items, (trend) => trend.count),
      (trend) => trend.date,
    );
    const entries = Array.from(dateCounts, ([date, count]) => ({ date, count })).sort(
      (a, b) => a.date.localeCompare(b.date),
    );

    if (entries.length === 0) return;

    const x = d3
      .scaleBand()
      .domain(entries.map((entry) => entry.date))
      .range([margin.left, width - margin.right])
      .padding(0.2);

    const y = d3
      .scaleLinear()
      .domain([0, d3.max(entries, (entry) => entry.count) ?? 0])
      .nice()
      .range([height - margin.bottom, margin.top]);

    const line = d3
      .line<{ date: string; count: number }>()
      .x((entry) => x(entry.date)! + x.bandwidth() / 2)
      .y((entry) => y(entry.count))
      .curve(d3.curveMonotoneX);

    svg
      .append('path')
      .datum(entries)
      .attr('d', line)
      .attr('fill', 'none')
      .attr('stroke', DARK_THEME.accent)
      .attr('stroke-width', 2);

    svg
      .selectAll('circle')
      .data(entries)
      .join('circle')
      .attr('cx', (entry) => x(entry.date)! + x.bandwidth() / 2)
      .attr('cy', (entry) => y(entry.count))
      .attr('r', 3)
      .attr('fill', DARK_THEME.accent);

    svg
      .append('g')
      .attr('transform', `translate(0,${height - margin.bottom})`)
      .call(
        d3
          .axisBottom(x)
          .tickValues(x.domain().filter((_, index) => index % Math.ceil(entries.length / 6) === 0)),
      )
      .selectAll('text')
      .attr('fill', DARK_THEME.textMuted)
      .attr('font-size', '10px');

    svg.selectAll('.domain, .tick line').attr('stroke', DARK_THEME.border);

    svg
      .append('g')
      .attr('transform', `translate(${margin.left},0)`)
      .call(d3.axisLeft(y).ticks(5))
      .selectAll('text')
      .attr('fill', DARK_THEME.textMuted);
  }

  severityBadge(severity: 'H' | 'M' | 'L'): string {
    const base = 'text-[10px] font-medium px-2 py-0.5 rounded-full ';
    switch (severity) {
      case 'H':
        return base + 'bg-red-900/40 text-red-400';
      case 'M':
        return base + 'bg-yellow-900/40 text-yellow-400';
      case 'L':
      default:
        return base + 'bg-sky-900/40 text-sky-400';
    }
  }
}
