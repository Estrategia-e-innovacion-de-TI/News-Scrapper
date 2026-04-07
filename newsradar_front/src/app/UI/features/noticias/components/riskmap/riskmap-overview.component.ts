import { DecimalPipe } from '@angular/common';
import { Component, input, output } from '@angular/core';

import { RiskSignal, RiskmapCluster, RiskmapData } from '../../../../../domain/noticias/models';

@Component({
  selector: 'app-riskmap-overview',
  standalone: true,
  imports: [DecimalPipe],
  template: `
    <div class="space-y-6">
      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        @for (card of kpis(); track card.label) {
          <div class="rounded-2xl border border-dark-border bg-dark-surface p-4">
            <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">{{ card.label }}</p>
            <p class="mt-2 text-2xl font-semibold text-dark-text">{{ card.value }}</p>
          </div>
        }
      </div>

      <div class="grid gap-6 xl:grid-cols-[1.35fr_1fr]">
        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h4 class="text-sm font-semibold text-dark-text">Lectura ejecutiva</h4>
          <p class="mt-3 text-sm leading-6 text-dark-text/90">
            {{ data().summary.executive_summary || 'Sin resumen ejecutivo disponible.' }}
          </p>
          @if ((data().summary.dominant_risks ?? []).length > 0) {
            <div class="mt-4 flex flex-wrap gap-2">
              @for (risk of data().summary.dominant_risks ?? []; track risk) {
                <span class="rounded-full border border-dark-border bg-dark-bg px-3 py-1 text-xs text-dark-muted">
                  {{ risk }}
                </span>
              }
            </div>
          }
        </section>

        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h4 class="text-sm font-semibold text-dark-text">Cobertura metodologica</h4>
          <div class="mt-4 grid grid-cols-2 gap-3">
            <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
              <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Coherencia</p>
              <p class="mt-2 text-xl font-semibold text-dark-text">{{ data().quality_checks?.cluster_coherence_avg ?? 0 }}</p>
            </div>
            <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
              <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Calidad</p>
              <p class="mt-2 text-xl font-semibold text-dark-text">{{ data().quality_checks?.cluster_quality_avg ?? 0 }}</p>
            </div>
            <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
              <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Taxonomia</p>
              <p class="mt-2 text-xl font-semibold text-dark-text">{{ data().quality_checks?.taxonomy_coverage ?? 0 }}%</p>
            </div>
            <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
              <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Weak signals</p>
              <p class="mt-2 text-xl font-semibold text-dark-text">{{ data().quality_checks?.weak_signal_clusters ?? 0 }}</p>
            </div>
          </div>
        </section>
      </div>

      <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
        <h4 class="text-sm font-semibold text-dark-text">Cluster cards de riesgo</h4>
        <p class="mt-1 text-xs text-dark-muted">
          Lectura priorizada por severidad, momentum, persistencia y novedad.
        </p>
        <div class="mt-4 grid gap-4 xl:grid-cols-3">
          @for (cluster of clusters().slice(0, 6); track cluster.cluster_id) {
            <button
              class="rounded-3xl border border-dark-border bg-dark-bg/60 p-5 text-left transition hover:border-yellow-400 hover:bg-yellow-50"
              type="button"
              (click)="clusterSelected.emit(cluster)"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <p class="text-[11px] uppercase tracking-[0.16em] text-dark-muted">
                    {{ cluster.dominant_risk || cluster.category }}
                  </p>
                  <h5 class="mt-2 text-lg font-semibold leading-6 text-dark-text">{{ cluster.label }}</h5>
                  <p class="mt-2 text-xs leading-5 text-dark-muted">{{ cluster.subtitle }}</p>
                </div>
                <span [class]="stageBadge(cluster.hype_stage)">{{ stageLabel(cluster.hype_stage) }}</span>
              </div>
              <p class="mt-4 text-sm leading-6 text-dark-text/90">
                {{ cluster.executive_takeaway || cluster.summary }}
              </p>
              <div class="mt-4 grid grid-cols-4 gap-2 text-xs">
                <div class="rounded-lg bg-dark-surface px-2 py-2">
                  <p class="text-dark-muted">Severidad</p>
                  <p class="mt-1 font-medium text-dark-text">{{ cluster.risk_severity | number:'1.0-0' }}</p>
                </div>
                <div class="rounded-lg bg-dark-surface px-2 py-2">
                  <p class="text-dark-muted">Impacto</p>
                  <p class="mt-1 font-medium text-dark-text">{{ cluster.impact_score | number:'1.0-0' }}</p>
                </div>
                <div class="rounded-lg bg-dark-surface px-2 py-2">
                  <p class="text-dark-muted">Momentum</p>
                  <p class="mt-1 font-medium text-dark-text">{{ cluster.momentum_score | number:'1.0-0' }}</p>
                </div>
                <div class="rounded-lg bg-dark-surface px-2 py-2">
                  <p class="text-dark-muted">Persistencia</p>
                  <p class="mt-1 font-medium text-dark-text">{{ cluster.persistence_score | number:'1.0-0' }}</p>
                </div>
              </div>
            </button>
          }
        </div>
      </section>

      <div class="grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <section class="min-w-0 overflow-hidden rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h4 class="text-sm font-semibold text-dark-text">Taxonomia y temporalidad</h4>
          <div class="mt-4 space-y-4">
            <div>
              <p class="text-xs uppercase tracking-[0.18em] text-dark-muted">Taxonomia dominante</p>
              <div class="mt-3 space-y-2">
                @for (item of taxonomyBreakdown().slice(0, 8); track item.name) {
                  <div>
                    <div class="flex min-w-0 items-center justify-between gap-3 text-xs text-dark-muted">
                      <span class="min-w-0 truncate" [title]="item.name">{{ item.name }}</span>
                      <span class="shrink-0">{{ item.score | number:'1.0-2' }}</span>
                    </div>
                    <div class="mt-1 h-2 w-full overflow-hidden rounded-full bg-dark-border">
                      <div class="h-full rounded-full bg-amber-500" [style.width.%]="ratio(item.score, taxonomyMax())"></div>
                    </div>
                  </div>
                }
              </div>
            </div>
            <div>
              <p class="text-xs uppercase tracking-[0.18em] text-dark-muted">Volumen mensual</p>
              <div class="mt-3 space-y-2">
                @for (item of monthlyVolume().slice(-8); track item.bucket) {
                  <div>
                    <div class="flex min-w-0 items-center justify-between gap-3 text-xs text-dark-muted">
                      <span class="min-w-0 truncate">{{ item.bucket }}</span>
                      <span class="shrink-0">{{ item.count }}</span>
                    </div>
                    <div class="mt-1 h-2 w-full overflow-hidden rounded-full bg-dark-border">
                      <div class="h-full rounded-full bg-emerald-400" [style.width.%]="ratio(item.count, monthlyVolumeMax())"></div>
                    </div>
                  </div>
                }
              </div>
            </div>
          </div>
        </section>

        <section class="min-w-0 overflow-hidden rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h4 class="text-sm font-semibold text-dark-text">Senales e insights</h4>
          <div class="mt-4 space-y-3">
            @for (signal of topSignals().slice(0, 5); track signal.type + signal.description) {
              <div class="rounded-xl border border-dark-border bg-dark-bg/60 p-3">
                <div class="flex items-center justify-between gap-3">
                  <span class="text-sm font-medium text-dark-text">{{ signal.type }}</span>
                  <span [class]="severityBadge(signal.severity)">{{ signal.severity }}</span>
                </div>
                <p class="mt-2 text-sm leading-6 text-dark-muted">{{ signal.description }}</p>
              </div>
            }
          </div>
        </section>
      </div>

      <div class="grid gap-6 xl:grid-cols-2">
        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h4 class="text-sm font-semibold text-dark-text">Insights</h4>
          <div class="mt-4 space-y-3">
            @for (item of data().insights; track item) {
              <div class="rounded-xl border border-dark-border bg-dark-bg/60 px-3 py-3 text-sm leading-6 text-dark-text/90">
                {{ item }}
              </div>
            }
          </div>
        </section>

        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h4 class="text-sm font-semibold text-dark-text">Recomendaciones</h4>
          <div class="mt-4 space-y-3">
            @for (item of data().recommendations; track item) {
              <div class="rounded-xl border border-dark-border bg-dark-bg/60 px-3 py-3 text-sm leading-6 text-dark-text/90">
                {{ item }}
              </div>
            }
          </div>
        </section>
      </div>
    </div>
  `,
})
export class RiskmapOverviewComponent {
  readonly data = input.required<RiskmapData>();
  readonly clusters = input.required<RiskmapCluster[]>();
  readonly clusterSelected = output<RiskmapCluster>();

  kpis() {
    const data = this.data();
    return [
      { label: 'Documentos', value: data.summary.total_documents ?? data.meta.total_filtered },
      { label: 'Clusters', value: data.meta.total_clusters },
      { label: 'Weak', value: data.quality_checks?.weak_signal_clusters ?? 0 },
      { label: 'Taxonomia', value: `${data.quality_checks?.taxonomy_coverage ?? 0}%` },
      { label: 'Sin cluster', value: data.summary.unclustered_documents ?? 0 },
      { label: 'Fuentes', value: data.filters_metadata?.sources.length ?? 0 },
    ];
  }

  taxonomyBreakdown(): Array<{ name: string; score: number }> {
    return this.data().taxonomy_breakdown ?? [];
  }

  monthlyVolume(): Array<{ bucket: string; count: number }> {
    return (this.data().charts?.['monthly_volume'] as Array<{ bucket: string; count: number }> | undefined) ?? [];
  }

  topSignals(): RiskSignal[] {
    return this.data().risk_signals ?? [];
  }

  taxonomyMax(): number {
    return Math.max(...this.taxonomyBreakdown().map((item) => item.score), 0);
  }

  monthlyVolumeMax(): number {
    return Math.max(...this.monthlyVolume().map((item) => item.count), 0);
  }

  ratio(value: number, max: number): number {
    return !max ? 0 : Math.max(0, Math.min(100, (value / max) * 100));
  }

  stageLabel(value: string): string {
    return value.replaceAll('_', ' ');
  }

  stageBadge(value: string): string {
    const base = 'rounded-full border px-2 py-1 text-[10px] font-medium ';
    if (value === 'weak_signal') return base + 'border-yellow-500 bg-yellow-100 text-yellow-900';
    if (value === 'correction') return base + 'border-rose-500 bg-rose-50 text-rose-700';
    if (value === 'productive_adoption' || value === 'consolidation') return base + 'border-emerald-500 bg-emerald-50 text-emerald-700';
    return base + 'border-sky-500 bg-sky-50 text-sky-700';
  }

  severityBadge(value: 'H' | 'M' | 'L'): string {
    const base = 'rounded-full border px-2 py-1 text-[10px] font-medium ';
    if (value === 'H') return base + 'border-rose-500 bg-rose-50 text-rose-700';
    if (value === 'M') return base + 'border-yellow-500 bg-yellow-100 text-yellow-900';
    return base + 'border-sky-500 bg-sky-50 text-sky-700';
  }
}
