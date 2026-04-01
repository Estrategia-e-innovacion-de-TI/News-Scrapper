import { DecimalPipe } from '@angular/common';
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

interface NamedScore {
  name: string;
  score: number;
}

interface VolumePoint {
  bucket: string;
  count: number;
}

@Component({
  selector: 'app-trendmap-overview',
  standalone: true,
  imports: [DecimalPipe],
  template: `
    <div class="space-y-6">
      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        @for (kpi of kpis(); track kpi.label) {
          <div class="rounded-2xl border border-dark-border bg-dark-surface p-4">
            <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">{{ kpi.label }}</p>
            <p class="mt-2 text-2xl font-semibold text-dark-text">{{ kpi.value }}</p>
          </div>
        }
      </div>

      <div class="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h4 class="text-sm font-semibold text-dark-text">Lectura ejecutiva</h4>
          <p class="mt-3 text-sm leading-6 text-dark-text/90">
            {{ data().summary.executive_summary || 'Sin resumen ejecutivo disponible.' }}
          </p>

          @if (headlineTags().length > 0) {
            <div class="mt-4 flex flex-wrap gap-2">
              @for (tag of headlineTags(); track tag) {
                <span class="rounded-full border border-dark-border bg-dark-bg px-3 py-1 text-xs text-dark-muted">
                  {{ tag }}
                </span>
              }
            </div>
          }

          @if (data().comparative_signals?.summary) {
            <div class="mt-4 rounded-2xl border border-dark-border bg-dark-bg/70 px-4 py-3 text-sm leading-6 text-dark-muted">
              {{ data().comparative_signals?.summary }}
            </div>
          }
        </section>

        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h4 class="text-sm font-semibold text-dark-text">Cobertura metodologica</h4>
          <div class="mt-4 grid grid-cols-2 gap-3">
            <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
              <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Coherencia</p>
              <p class="mt-2 text-xl font-semibold text-dark-text">
                {{ data().quality_checks?.cluster_coherence_avg ?? 0 }}
              </p>
            </div>
            <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
              <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Calidad promedio</p>
              <p class="mt-2 text-xl font-semibold text-dark-text">
                {{ data().quality_checks?.cluster_quality_avg ?? 0 }}
              </p>
            </div>
            <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
              <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Taxonomia</p>
              <p class="mt-2 text-xl font-semibold text-dark-text">
                {{ data().quality_checks?.taxonomy_coverage ?? 0 }}%
              </p>
            </div>
            <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
              <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Weak signals</p>
              <p class="mt-2 text-xl font-semibold text-dark-text">
                {{ data().quality_checks?.weak_signal_clusters ?? 0 }}
              </p>
            </div>
            <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
              <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Cobertura</p>
              <p class="mt-2 text-xl font-semibold text-dark-text">
                {{ (data().quality_checks?.cluster_coverage ?? (100 - (data().quality_checks?.unclustered_ratio ?? 0))) | number:'1.0-0' }}%
              </p>
            </div>
            <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
              <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Estabilidad</p>
              <p class="mt-2 text-xl font-semibold text-dark-text">
                {{ (data().quality_checks?.stability_score_avg ?? 0) | number:'1.0-0' }}
              </p>
            </div>
          </div>
        </section>
      </div>

      @if (clusterCards().length > 0) {
        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <div class="flex items-center justify-between gap-4">
            <div>
              <h4 class="text-sm font-semibold text-dark-text">Cluster cards</h4>
              <p class="mt-1 text-xs text-dark-muted">
                Narrativa priorizada por impacto y momentum.
              </p>
            </div>
          </div>

          <div class="mt-4 grid gap-4 xl:grid-cols-3">
            @for (card of clusterCards().slice(0, 6); track card.cluster_id) {
              <article class="rounded-3xl border border-dark-border bg-dark-bg/60 p-5">
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <div class="flex flex-wrap items-center gap-2">
                      <span
                        class="inline-flex items-center gap-2 rounded-full border border-dark-border bg-dark-surface px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-dark-muted"
                      >
                        <span
                          class="h-2.5 w-2.5 rounded-full"
                          [style.backgroundColor]="categoryColor(card.category)"
                        ></span>
                        {{ card.category }}
                      </span>
                      <span class="rounded-full border border-sky-500/30 bg-sky-500/10 px-2 py-1 text-[10px] text-sky-200">
                        {{ formatStage(card.hype_stage) }}
                      </span>
                      @if (card.comparative_signal) {
                        <span class="rounded-full border border-dark-border bg-dark-bg px-2 py-1 text-[10px] text-dark-muted">
                          {{ card.comparative_signal.status }}
                        </span>
                      }
                    </div>
                    <h5 class="mt-3 text-lg font-semibold leading-6 text-dark-text">{{ card.label }}</h5>
                    <p class="mt-2 text-xs leading-5 text-dark-muted">{{ card.subtitle }}</p>
                  </div>
                  @if (card.weak_signal_flag) {
                    <span class="rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-1 text-[10px] text-amber-300">
                      weak signal
                    </span>
                  }
                </div>

                <div class="mt-4 space-y-3">
                  <div class="rounded-2xl border border-dark-border bg-dark-surface/70 p-3">
                    <p class="text-[11px] uppercase tracking-[0.14em] text-dark-muted">Lectura estrategica</p>
                    <p class="mt-2 text-sm leading-6 text-dark-text/90">
                      {{ card.executive_takeaway || card.summary }}
                    </p>
                  </div>

                  @if (card.why_it_matters) {
                    <div class="rounded-2xl border border-dark-border bg-dark-surface/60 p-3">
                      <p class="text-[11px] uppercase tracking-[0.14em] text-dark-muted">Por que importa</p>
                      <p class="mt-2 text-sm leading-6 text-dark-muted">
                        {{ card.why_it_matters }}
                      </p>
                    </div>
                  }

                  @if (card.decision_prompt) {
                    <div class="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-3">
                      <p class="text-[11px] uppercase tracking-[0.14em] text-amber-200">Decision sugerida</p>
                      <p class="mt-2 text-sm leading-6 text-dark-text/90">
                        {{ card.decision_prompt }}
                      </p>
                    </div>
                  }
                </div>

                <div class="mt-4 grid grid-cols-4 gap-2 text-xs">
                  <div class="rounded-lg bg-dark-surface px-2 py-2">
                    <p class="text-dark-muted">Impacto</p>
                    <p class="mt-1 font-medium text-dark-text">{{ card.impact_score }}</p>
                  </div>
                  <div class="rounded-lg bg-dark-surface px-2 py-2">
                    <p class="text-dark-muted">Madurez</p>
                    <p class="mt-1 font-medium text-dark-text">{{ card.maturity_score }}</p>
                  </div>
                  <div class="rounded-lg bg-dark-surface px-2 py-2">
                    <p class="text-dark-muted">Momentum</p>
                    <p class="mt-1 font-medium text-dark-text">{{ card.momentum_score }}</p>
                  </div>
                  <div class="rounded-lg bg-dark-surface px-2 py-2">
                    <p class="text-dark-muted">Calidad</p>
                    <p class="mt-1 font-medium text-dark-text">{{ card.quality_score }}</p>
                  </div>
                </div>

                @if (card.evidence_line) {
                  <div class="mt-4 rounded-2xl border border-dark-border bg-dark-surface/60 p-3">
                    <p class="text-[11px] uppercase tracking-[0.14em] text-dark-muted">Evidencia</p>
                    <p class="mt-2 text-sm leading-6 text-dark-muted">
                      {{ card.evidence_line }}
                    </p>
                  </div>
                }

                @if ((card.impact_targets?.length ?? 0) > 0) {
                  <div class="mt-4 flex flex-wrap gap-2">
                    @for (target of (card.impact_targets ?? []).slice(0, 3); track target) {
                      <span class="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-[11px] text-emerald-200">
                        {{ target }}
                      </span>
                    }
                  </div>
                }

                <div class="mt-4 flex flex-wrap gap-2">
                  @for (kw of card.top_keywords.slice(0, 4); track kw) {
                    <span class="rounded-full border border-dark-border bg-dark-surface px-2 py-1 text-[11px] text-dark-muted">
                      {{ kw }}
                    </span>
                  }
                </div>
              </article>
            }
          </div>
        </section>
      }

      <div class="grid gap-6 xl:grid-cols-2">
        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h4 class="text-sm font-semibold text-dark-text">Taxonomia dominante</h4>
          <p class="mt-1 text-xs text-dark-muted">
            Peso agregado de matches taxonomicos sobre clusters detectados.
          </p>
          <svg #taxonomyChart></svg>
        </section>

        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h4 class="text-sm font-semibold text-dark-text">Volumen mensual</h4>
          <p class="mt-1 text-xs text-dark-muted">
            Evolucion del corpus analizado dentro de la ventana del snapshot.
          </p>
          <svg #monthlyChart></svg>
        </section>
      </div>

      <div class="grid gap-6 xl:grid-cols-3">
        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h4 class="text-sm font-semibold text-dark-text">Insights</h4>
          @if (data().insights.length === 0) {
            <p class="mt-3 text-sm text-dark-muted">No hay insights disponibles.</p>
          } @else {
            <div class="mt-4 space-y-3">
              @for (item of data().insights; track item) {
                <div class="rounded-xl border border-dark-border bg-dark-bg/60 px-3 py-3 text-sm leading-6 text-dark-text/90">
                  {{ item }}
                </div>
              }
            </div>
          }
        </section>

        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h4 class="text-sm font-semibold text-dark-text">Recomendaciones</h4>
          @if (data().recommendations.length === 0) {
            <p class="mt-3 text-sm text-dark-muted">No hay recomendaciones disponibles.</p>
          } @else {
            <div class="mt-4 space-y-3">
              @for (item of data().recommendations; track item) {
                <div class="rounded-xl border border-dark-border bg-dark-bg/60 px-3 py-3 text-sm leading-6 text-dark-text/90">
                  {{ item }}
                </div>
              }
            </div>
          }
        </section>

        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h4 class="text-sm font-semibold text-dark-text">Weak signals</h4>
          @if (weakSignals().length === 0) {
            <p class="mt-3 text-sm text-dark-muted">No se detectaron weak signals destacados.</p>
          } @else {
            <div class="mt-4 space-y-3">
              @for (item of weakSignals().slice(0, 4); track item.cluster_id) {
                <div class="rounded-xl border border-dark-border bg-dark-bg/60 p-3">
                  <div class="flex items-start justify-between gap-3">
                    <div>
                      <p class="text-sm font-medium text-dark-text">{{ item.label }}</p>
                      <p class="mt-1 text-xs text-dark-muted">{{ item.subtitle }}</p>
                    </div>
                    <span class="rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-1 text-[10px] text-amber-300">
                      {{ item.hype_stage.replaceAll('_', ' ') }}
                    </span>
                  </div>
                  <p class="mt-2 text-xs leading-5 text-dark-muted">{{ item.summary }}</p>
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
  readonly taxonomyChartRef = viewChild.required<ElementRef<SVGSVGElement>>('taxonomyChart');
  readonly monthlyChartRef = viewChild.required<ElementRef<SVGSVGElement>>('monthlyChart');

  private initialized = false;

  constructor() {
    effect(() => {
      const snapshot = this.data();
      if (this.initialized && snapshot) {
        this.renderTaxonomyChart(this.taxonomyData(snapshot));
        this.renderMonthlyChart(this.monthlyVolume(snapshot));
      }
    });
  }

  ngAfterViewInit(): void {
    this.initialized = true;
    const snapshot = this.data();
    this.renderTaxonomyChart(this.taxonomyData(snapshot));
    this.renderMonthlyChart(this.monthlyVolume(snapshot));
  }

  kpis(): KpiCard[] {
    const snapshot = this.data();
    return [
      { label: 'Documentos', value: snapshot.summary.total_documents ?? snapshot.meta.total_filtered },
      { label: 'Clusters', value: snapshot.meta.total_clusters },
      { label: 'Sin cluster', value: snapshot.summary.unclustered_documents ?? 0 },
      { label: 'Fuentes', value: snapshot.filters_metadata?.sources.length ?? 0 },
      { label: 'Taxonomia', value: `${snapshot.quality_checks?.taxonomy_coverage ?? 0}%` },
      { label: 'Weak signals', value: snapshot.quality_checks?.weak_signal_clusters ?? 0 },
    ];
  }

  headlineTags(): string[] {
    const summary = this.data().summary;
    return [
      ...(summary.dominant_topics ?? []),
      ...(summary.emerging_topics ?? []),
      ...(summary.consolidating_topics ?? []),
      ...(summary.weak_signal_topics ?? []),
    ].slice(0, 8);
  }

  clusterCards() {
    return this.data().cluster_cards ?? [];
  }

  weakSignals() {
    return this.data().weak_signals ?? [];
  }

  formatStage(stage: string): string {
    return stage.replaceAll('_', ' ');
  }

  categoryColor(category: string): string {
    const palette = ['#38bdf8', '#f59e0b', '#34d399', '#fb7185', '#818cf8', '#f97316'];
    const hash = [...category].reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return palette[hash % palette.length];
  }

  private taxonomyData(snapshot: TrendmapData): NamedScore[] {
    return (snapshot.taxonomy_breakdown ?? []).slice(0, 8);
  }

  private monthlyVolume(snapshot: TrendmapData): VolumePoint[] {
    return (
      (snapshot.charts?.['monthly_volume'] as VolumePoint[] | undefined) ??
      []
    );
  }

  private renderTaxonomyChart(data: NamedScore[]): void {
    const svg = d3.select(this.taxonomyChartRef().nativeElement);
    svg.selectAll('*').remove();

    const width = 520;
    const rowHeight = 38;
    const height = Math.max(220, data.length * rowHeight + 40);
    const margin = { top: 10, right: 24, bottom: 24, left: 170 };

    svg.attr('width', width).attr('height', height);

    if (data.length === 0) {
      svg
        .append('text')
        .attr('x', width / 2)
        .attr('y', height / 2)
        .attr('text-anchor', 'middle')
        .attr('fill', DARK_THEME.textMuted)
        .text('Sin datos taxonomicos');
      return;
    }

    const x = d3
      .scaleLinear()
      .domain([0, d3.max(data, (d) => d.score) ?? 1])
      .nice()
      .range([margin.left, width - margin.right]);

    const y = d3
      .scaleBand()
      .domain(data.map((d) => d.name))
      .range([margin.top, height - margin.bottom])
      .padding(0.25);

    svg
      .append('g')
      .selectAll('rect')
      .data(data)
      .join('rect')
      .attr('x', margin.left)
      .attr('y', (d) => y(d.name) ?? 0)
      .attr('width', (d) => x(d.score) - margin.left)
      .attr('height', y.bandwidth())
      .attr('fill', DARK_THEME.accent)
      .attr('rx', 8);

    svg
      .append('g')
      .attr('transform', `translate(0,${height - margin.bottom})`)
      .call(d3.axisBottom(x).ticks(4))
      .selectAll('text')
      .attr('fill', DARK_THEME.textMuted)
      .attr('font-size', '10px');

    svg.selectAll('.domain, .tick line').attr('stroke', DARK_THEME.border);

    svg
      .append('g')
      .attr('transform', `translate(${margin.left},0)`)
      .call(d3.axisLeft(y))
      .selectAll('text')
      .attr('fill', DARK_THEME.text)
      .attr('font-size', '11px');

    svg
      .append('g')
      .selectAll('text.value')
      .data(data)
      .join('text')
      .attr('x', (d) => x(d.score) + 8)
      .attr('y', (d) => (y(d.name) ?? 0) + y.bandwidth() / 2)
      .attr('dominant-baseline', 'central')
      .attr('fill', DARK_THEME.textMuted)
      .attr('font-size', '11px')
      .text((d) => d.score.toFixed(2));
  }

  private renderMonthlyChart(data: VolumePoint[]): void {
    const svg = d3.select(this.monthlyChartRef().nativeElement);
    svg.selectAll('*').remove();

    const width = 520;
    const height = 280;
    const margin = { top: 12, right: 18, bottom: 42, left: 44 };

    svg.attr('width', width).attr('height', height);

    if (data.length === 0) {
      svg
        .append('text')
        .attr('x', width / 2)
        .attr('y', height / 2)
        .attr('text-anchor', 'middle')
        .attr('fill', DARK_THEME.textMuted)
        .text('Sin volumen mensual');
      return;
    }

    const x = d3
      .scalePoint()
      .domain(data.map((d) => d.bucket))
      .range([margin.left, width - margin.right]);

    const y = d3
      .scaleLinear()
      .domain([0, d3.max(data, (d) => d.count) ?? 0])
      .nice()
      .range([height - margin.bottom, margin.top]);

    const line = d3
      .line<VolumePoint>()
      .x((d) => x(d.bucket) ?? margin.left)
      .y((d) => y(d.count))
      .curve(d3.curveMonotoneX);

    svg
      .append('path')
      .datum(data)
      .attr('fill', 'none')
      .attr('stroke', DARK_THEME.accent)
      .attr('stroke-width', 2.5)
      .attr('d', line);

    svg
      .append('g')
      .selectAll('circle')
      .data(data)
      .join('circle')
      .attr('cx', (d) => x(d.bucket) ?? margin.left)
      .attr('cy', (d) => y(d.count))
      .attr('r', 4)
      .attr('fill', DARK_THEME.accent);

    svg
      .append('g')
      .attr('transform', `translate(0,${height - margin.bottom})`)
      .call(
        d3
          .axisBottom(x)
          .tickValues(
            x
              .domain()
              .filter((_, index) => index % Math.max(1, Math.ceil(data.length / 6)) === 0),
          ),
      )
      .selectAll('text')
      .attr('fill', DARK_THEME.textMuted)
      .attr('font-size', '10px');

    svg
      .append('g')
      .attr('transform', `translate(${margin.left},0)`)
      .call(d3.axisLeft(y).ticks(5))
      .selectAll('text')
      .attr('fill', DARK_THEME.textMuted)
      .attr('font-size', '10px');

    svg.selectAll('.domain, .tick line').attr('stroke', DARK_THEME.border);
  }
}
