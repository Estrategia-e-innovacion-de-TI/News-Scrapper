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

interface MethodologyMetricCard {
  label: string;
  value: number;
  suffix?: string;
  help: string;
  interpretation: string;
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
            @for (metric of methodologyMetrics(); track metric.label) {
              <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
                <div class="flex items-center gap-2">
                  <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">{{ metric.label }}</p>
                  <span
                    class="inline-flex h-4 w-4 cursor-help items-center justify-center rounded-full border border-dark-border bg-white text-[10px] font-semibold text-dark-muted"
                    [attr.title]="metric.help + ' Interpretacion: ' + metric.interpretation"
                    aria-label="Ayuda de metrica"
                  >
                    i
                  </span>
                </div>
                <p class="mt-2 text-xl font-semibold text-dark-text">
                  {{ metric.value | number:'1.0-1' }}{{ metric.suffix ?? '' }}
                </p>
                <p class="mt-1 text-xs leading-5 text-dark-muted">{{ metric.interpretation }}</p>
              </div>
            }
          </div>
        </section>
      </div>

      @if (clusterCards().length > 0) {
        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <div class="flex items-center justify-between gap-4">
            <div>
              <h4 class="text-sm font-semibold text-dark-text">Tarjetas de agrupaciones</h4>
              <p class="mt-1 text-xs text-dark-muted">
                Narrativa priorizada por impacto y dinamica.
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
                      <span class="rounded-full border border-sky-500 bg-sky-50 px-2 py-1 text-[10px] text-sky-700">
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
                    <span class="rounded-full border border-yellow-500 bg-yellow-100 px-2 py-1 text-[10px] text-yellow-900">
                      señal temprana
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
                      <p class="text-[11px] uppercase tracking-[0.14em] text-yellow-800">Decision sugerida</p>
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
                    <p class="text-dark-muted">Dinamica</p>
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
                      <span class="rounded-full border border-emerald-500 bg-emerald-50 px-3 py-1 text-[11px] text-emerald-700">
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

      <div class="grid gap-6 2xl:grid-cols-2">
        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h4 class="text-sm font-semibold text-dark-text">Taxonomia dominante</h4>
          <p class="mt-1 text-xs text-dark-muted">
            Peso agregado de matches taxonomicos sobre clusters detectados.
          </p>
          <svg #taxonomyChart class="mt-3 h-auto w-full max-w-full overflow-visible"></svg>
        </section>

        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h4 class="text-sm font-semibold text-dark-text">Volumen mensual</h4>
          <p class="mt-1 text-xs text-dark-muted">
            Evolucion del corpus analizado dentro de la ventana del snapshot.
          </p>
          <svg #monthlyChart class="mt-3 h-auto w-full max-w-full overflow-visible"></svg>
        </section>
      </div>

      <div class="grid gap-6 xl:grid-cols-3">
        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h4 class="text-sm font-semibold text-dark-text">Hallazgos clave</h4>
          @if (data().insights.length === 0) {
            <p class="mt-3 text-sm text-dark-muted">No hay hallazgos disponibles.</p>
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
          <h4 class="text-sm font-semibold text-dark-text">Señales tempranas</h4>
          @if (weakSignals().length === 0) {
            <p class="mt-3 text-sm text-dark-muted">No se detectaron señales tempranas destacadas.</p>
          } @else {
            <div class="mt-4 space-y-3">
              @for (item of weakSignals().slice(0, 4); track item.cluster_id) {
                <div class="rounded-xl border border-dark-border bg-dark-bg/60 p-3">
                  <div class="flex items-start justify-between gap-3">
                    <div>
                      <p class="text-sm font-medium text-dark-text">{{ item.label }}</p>
                      <p class="mt-1 text-xs text-dark-muted">{{ item.subtitle }}</p>
                    </div>
                    <span class="rounded-full border border-yellow-500 bg-yellow-100 px-2 py-1 text-[10px] text-yellow-900">
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
      { label: 'Señales tempranas', value: snapshot.quality_checks?.weak_signal_clusters ?? 0 },
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

  methodologyMetrics(): MethodologyMetricCard[] {
    const quality = this.data().quality_checks;
    const coherence = quality?.cluster_coherence_avg ?? 0;
    const avgQuality = quality?.cluster_quality_avg ?? 0;
    const taxonomy = quality?.taxonomy_coverage ?? 0;
    const weakSignals = quality?.weak_signal_clusters ?? 0;
    const coverage = quality?.cluster_coverage ?? (100 - (quality?.unclustered_ratio ?? 0));
    const stability = quality?.stability_score_avg ?? 0;

    return [
      {
        label: 'Coherencia',
        value: coherence,
        help: 'Mide que tan consistentes son los documentos dentro de cada cluster.',
        interpretation: this.interpretScore(coherence, 'Alta coherencia entre documentos.'),
      },
      {
        label: 'Calidad promedio',
        value: avgQuality,
        help: 'Resume la calidad analitica de los clusters segun relevancia, consistencia y evidencia.',
        interpretation: this.interpretScore(avgQuality, 'Calidad analitica alta y confiable.'),
      },
      {
        label: 'Taxonomia',
        value: taxonomy,
        suffix: '%',
        help: 'Indica cuanto del corpus queda bien cubierto por la taxonomia definida.',
        interpretation: this.interpretScore(taxonomy, 'Excelente alineacion con la taxonomia.'),
      },
      {
        label: 'Señales tempranas',
        value: weakSignals,
        help: 'Cuenta clusters emergentes de baja madurez y alta novedad que requieren seguimiento.',
        interpretation: this.interpretWeakSignals(weakSignals),
      },
      {
        label: 'Cobertura',
        value: coverage,
        suffix: '%',
        help: 'Mide el porcentaje de documentos que lograron ser agrupados en clusters utiles.',
        interpretation: this.interpretScore(coverage, 'Cobertura alta del corpus en clusters.'),
      },
      {
        label: 'Estabilidad',
        value: stability,
        help: 'Mide que tan estable es la señal entre snapshots (menos volatilidad, mayor estabilidad).',
        interpretation: this.interpretStability(stability),
      },
    ];
  }

  private interpretScore(value: number, highText: string): string {
    if (value >= 80) {
      return `${highText} (${value.toFixed(1)})`;
    }
    if (value >= 60) {
      return `Nivel medio: conviene monitorear para fortalecerlo. (${value.toFixed(1)})`;
    }
    return `Nivel bajo: requiere ajustes de fuentes, taxonomia o clusterizacion. (${value.toFixed(1)})`;
  }

  private interpretWeakSignals(value: number): string {
    if (value === 0) {
      return 'No se detectan señales tempranas destacadas en este snapshot.';
    }
    if (value <= 3) {
      return `Hay ${value} señales tempranas: foco exploratorio acotado y manejable.`;
    }
    if (value <= 8) {
      return `Hay ${value} señales tempranas: buen nivel de exploracion para vigilancia activa.`;
    }
    return `Hay ${value} señales tempranas: alta exploracion, revisar priorizacion para evitar ruido.`;
  }

  private interpretStability(value: number): string {
    if (value >= 80) {
      return `Estabilidad alta: la señal es consistente entre periodos. (${value.toFixed(1)})`;
    }
    if (value >= 60) {
      return `Estabilidad media: hay cambios esperados pero aun es interpretable. (${value.toFixed(1)})`;
    }
    return `Estabilidad baja: la señal es volatil y requiere confirmacion adicional. (${value.toFixed(1)})`;
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

    const width = 680;
    const rowHeight = 38;
    const height = Math.max(220, data.length * rowHeight + 40);
    const margin = { top: 10, right: 56, bottom: 24, left: 230 };

    svg
      .attr('width', '100%')
      .attr('height', height)
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('preserveAspectRatio', 'xMidYMid meet');

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
      .call(d3.axisLeft(y).tickFormat((value) => this.shortChartLabel(String(value), 28)))
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

    const width = 680;
    const height = 280;
    const margin = { top: 12, right: 28, bottom: 42, left: 48 };

    svg
      .attr('width', '100%')
      .attr('height', height)
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('preserveAspectRatio', 'xMidYMid meet');

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

  private shortChartLabel(value: string, maxLength: number): string {
    return value.length > maxLength ? `${value.slice(0, maxLength - 3)}...` : value;
  }
}
