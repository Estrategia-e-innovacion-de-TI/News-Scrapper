import { DecimalPipe } from '@angular/common';
import { Component, computed, input, output } from '@angular/core';

import { DARK_THEME, LifecycleStage, RiskmapCluster } from '../../../../../domain/noticias/models';

type RiskSort = 'severity' | 'momentum' | 'persistence' | 'impact' | 'novelty' | 'size';
type RiskBand = 'low' | 'medium' | 'high';

@Component({
  selector: 'app-riskmap-map',
  standalone: true,
  imports: [DecimalPipe],
  template: `
    <div class="grid gap-6 xl:grid-cols-[320px_1fr]">
      <aside class="space-y-4">
        <section class="rounded-2xl border border-dark-border bg-dark-surface p-4">
          <div class="flex items-center justify-between gap-3">
            <div>
              <h4 class="text-sm font-semibold text-dark-text">Filtros</h4>
              <p class="mt-1 text-xs text-dark-muted">Categoria, fuente, stage y orden.</p>
            </div>
            <button
              class="rounded-full border border-dark-border bg-dark-bg px-3 py-1 text-[11px] text-dark-muted"
              type="button"
              (click)="clearRequested.emit()"
            >
              Limpiar
            </button>
          </div>

          <div class="mt-4 grid gap-3">
            <label class="grid gap-1">
              <span class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Categoria</span>
              <select
                class="rounded-xl border border-dark-border bg-dark-bg px-3 py-2 text-sm text-dark-text"
                [value]="filterCategory() ?? ''"
                (change)="categoryChanged.emit(onSelectValue($event))"
              >
                <option value="">Todas</option>
                @for (item of categories(); track item) {
                  <option [value]="item">{{ item }}</option>
                }
              </select>
            </label>

            <label class="grid gap-1">
              <span class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Tipo fuente</span>
              <select
                class="rounded-xl border border-dark-border bg-dark-bg px-3 py-2 text-sm text-dark-text"
                [value]="filterSourceType() ?? ''"
                (change)="sourceTypeChanged.emit(onSelectValue($event))"
              >
                <option value="">Todas</option>
                @for (item of sourceTypes(); track item) {
                  <option [value]="item">{{ item }}</option>
                }
              </select>
            </label>

            <label class="grid gap-1">
              <span class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Stage</span>
              <select
                class="rounded-xl border border-dark-border bg-dark-bg px-3 py-2 text-sm text-dark-text"
                [value]="filterHypeStage() ?? ''"
                (change)="hypeStageChanged.emit(onStageValue($event))"
              >
                <option value="">Todos</option>
                @for (item of hypeStages(); track item) {
                  <option [value]="item">{{ stageLabel(item) }}</option>
                }
              </select>
            </label>

            <label class="grid gap-1">
              <span class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Severidad</span>
              <select
                class="rounded-xl border border-dark-border bg-dark-bg px-3 py-2 text-sm text-dark-text"
                [value]="filterSeverityBand() ?? ''"
                (change)="severityBandChanged.emit(onBandValue($event))"
              >
                <option value="">Todas</option>
                @for (item of severityBands(); track item) {
                  <option [value]="item">{{ item }}</option>
                }
              </select>
            </label>

            <label class="grid gap-1">
              <span class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Novedad</span>
              <select
                class="rounded-xl border border-dark-border bg-dark-bg px-3 py-2 text-sm text-dark-text"
                [value]="filterNoveltyBand() ?? ''"
                (change)="noveltyBandChanged.emit(onBandValue($event))"
              >
                <option value="">Todas</option>
                @for (item of noveltyBands(); track item) {
                  <option [value]="item">{{ item }}</option>
                }
              </select>
            </label>

            <label class="grid gap-1">
              <span class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Orden</span>
              <select
                class="rounded-xl border border-dark-border bg-dark-bg px-3 py-2 text-sm text-dark-text"
                [value]="sortBy()"
                (change)="sortChanged.emit(onSortValue($event))"
              >
                @for (item of sortOptions(); track item.value) {
                  <option [value]="item.value">{{ item.label }}</option>
                }
              </select>
            </label>
          </div>

          <label class="mt-4 flex cursor-pointer items-start gap-3 rounded-xl border border-dark-border bg-dark-bg/70 px-3 py-2">
            <input
              class="mt-1 accent-amber-500"
              type="checkbox"
              [checked]="weakSignalsOnly()"
              (change)="weakSignalsChanged.emit(onCheckboxValue($event))"
            />
            <span>
              <span class="block text-sm text-dark-text">Solo weak signals</span>
              <span class="block text-xs text-dark-muted">Riesgos pequenos con alta novedad.</span>
            </span>
          </label>
        </section>

        <section class="rounded-2xl border border-dark-border bg-dark-surface p-4">
          <h4 class="text-sm font-semibold text-dark-text">Clusters de riesgo</h4>
          <p class="mt-1 text-xs text-dark-muted">{{ clusters().length }} visibles.</p>
          <div class="mt-4 max-h-[calc(100vh-18rem)] space-y-2 overflow-y-auto pr-1">
            @for (cluster of clusters(); track cluster.cluster_id) {
              <button
                class="w-full rounded-2xl border p-3 text-left transition cursor-pointer"
                [class]="clusterCardClass(cluster)"
                type="button"
                (click)="clusterSelected.emit(cluster)"
              >
                <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">
                  {{ cluster.dominant_risk || cluster.category }}
                </p>
                <h5 class="mt-1 text-sm font-semibold text-dark-text">{{ cluster.label }}</h5>
                <p class="mt-1 text-xs text-dark-muted">{{ cluster.subtitle }}</p>
                <div class="mt-3 grid grid-cols-3 gap-2 text-xs">
                  <div class="rounded-lg bg-dark-bg/70 px-2 py-2">
                    <p class="text-dark-muted">Severidad</p>
                    <p class="mt-1 font-medium text-dark-text">{{ cluster.risk_severity | number:'1.0-0' }}</p>
                  </div>
                  <div class="rounded-lg bg-dark-bg/70 px-2 py-2">
                    <p class="text-dark-muted">Momentum</p>
                    <p class="mt-1 font-medium text-dark-text">{{ cluster.momentum_score | number:'1.0-0' }}</p>
                  </div>
                  <div class="rounded-lg bg-dark-bg/70 px-2 py-2">
                    <p class="text-dark-muted">Docs</p>
                    <p class="mt-1 font-medium text-dark-text">{{ cluster.item_count }}</p>
                  </div>
                </div>
              </button>
            }
          </div>
        </section>
      </aside>

      <section class="rounded-2xl border border-dark-border bg-white p-5 shadow-sm">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h4 class="text-sm font-semibold text-dark-text">Mapa de clusterizacion</h4>
            <p class="mt-1 text-xs leading-5 text-dark-muted">
              Proyeccion semantica de clusters de riesgo. Tamano por volumen y color por categoria.
            </p>
          </div>
        </div>
        <svg viewBox="0 0 620 360" class="mt-4 h-auto w-full">
          <rect width="620" height="360" fill="#ffffff" rx="14" />
          @for (tick of axisTicks; track tick) {
            <line [attr.x1]="xAxis(tick)" [attr.x2]="xAxis(tick)" y1="36" y2="308" [attr.stroke]="theme.border" stroke-dasharray="4 6" />
            <line x1="56" x2="584" [attr.y1]="yAxis(tick)" [attr.y2]="yAxis(tick)" [attr.stroke]="theme.border" stroke-dasharray="4 6" />
          }
          <line x1="56" y1="308" x2="584" y2="308" [attr.stroke]="theme.border" />
          <line x1="56" y1="36" x2="56" y2="308" [attr.stroke]="theme.border" />
          <text x="320" y="344" text-anchor="middle" [attr.fill]="theme.textMuted" font-size="11">Separacion semantica</text>
          <text x="18" y="182" text-anchor="middle" [attr.fill]="theme.textMuted" font-size="11" transform="rotate(-90 18 182)">Afinidad documental</text>
          @for (point of points(); track point.cluster.cluster_id) {
            <g class="cursor-pointer" (click)="clusterSelected.emit(point.cluster)">
              <circle
                [attr.cx]="point.x"
                [attr.cy]="point.y"
                [attr.r]="point.r"
                [attr.fill]="point.color"
                [attr.opacity]="bubbleOpacity(point.cluster)"
                [attr.stroke]="selectedCluster()?.cluster_id === point.cluster.cluster_id ? '#2c2a29' : '#e2e8f0'"
                [attr.stroke-width]="selectedCluster()?.cluster_id === point.cluster.cluster_id ? 2 : 1.2"
              >
                <title>{{ point.cluster.label }}&#10;Categoria: {{ point.cluster.category }}&#10;Docs: {{ point.cluster.item_count }}&#10;Severidad: {{ point.cluster.risk_severity | number:'1.0-0' }}&#10;Momentum: {{ point.cluster.momentum_score | number:'1.0-0' }}</title>
              </circle>
              @if (point.r >= 12) {
                <text [attr.x]="point.x" [attr.y]="point.y - point.r - 8" text-anchor="middle" [attr.fill]="theme.text" font-size="9">
                  {{ shortLabel(point.cluster.label, 20) }}
                </text>
              }
            </g>
          }
        </svg>
      </section>
    </div>
  `,
})
export class RiskmapMapComponent {
  readonly clusters = input.required<RiskmapCluster[]>();
  readonly selectedCluster = input<RiskmapCluster | null>(null);
  readonly categories = input.required<string[]>();
  readonly sourceTypes = input.required<string[]>();
  readonly hypeStages = input.required<LifecycleStage[]>();
  readonly severityBands = input.required<RiskBand[]>();
  readonly noveltyBands = input.required<RiskBand[]>();
  readonly sortOptions = input.required<ReadonlyArray<{ readonly value: RiskSort; readonly label: string }>>();
  readonly filterCategory = input<string | null>(null);
  readonly filterSourceType = input<string | null>(null);
  readonly filterHypeStage = input<LifecycleStage | null>(null);
  readonly filterSeverityBand = input<RiskBand | null>(null);
  readonly filterNoveltyBand = input<RiskBand | null>(null);
  readonly weakSignalsOnly = input(false);
  readonly sortBy = input<RiskSort>('severity');
  readonly clusterSelected = output<RiskmapCluster>();
  readonly categoryChanged = output<string | null>();
  readonly sourceTypeChanged = output<string | null>();
  readonly hypeStageChanged = output<LifecycleStage | null>();
  readonly severityBandChanged = output<RiskBand | null>();
  readonly noveltyBandChanged = output<RiskBand | null>();
  readonly weakSignalsChanged = output<boolean>();
  readonly sortChanged = output<RiskSort>();
  readonly clearRequested = output<void>();

  readonly theme = DARK_THEME;
  readonly axisTicks = [0, 25, 50, 75, 100];

  readonly points = computed(() => {
    const items = this.clusters();
    const maxCount = Math.max(...items.map((cluster) => cluster.item_count), 1);
    const xs = items.map((cluster) => cluster.coords?.x ?? 0);
    const ys = items.map((cluster) => cluster.coords?.y ?? 0);
    const minX = Math.min(...xs, 0);
    const maxX = Math.max(...xs, 1);
    const minY = Math.min(...ys, 0);
    const maxY = Math.max(...ys, 1);
    return items.map((cluster) => ({
      cluster,
      x: this.scaleToRange(cluster.coords?.x ?? 0, minX, maxX, 56, 584),
      y: this.scaleToRange(cluster.coords?.y ?? 0, minY, maxY, 308, 36),
      r: 9 + (cluster.item_count / maxCount) * 20,
      color: this.colorFor(cluster.category),
    }));
  });

  clusterCardClass(cluster: RiskmapCluster): string {
    return this.selectedCluster()?.cluster_id === cluster.cluster_id
      ? 'border-yellow-500 bg-yellow-50'
      : 'border-dark-border bg-white hover:border-yellow-400 hover:bg-yellow-50';
  }

  xAxis(value: number): number {
    return 56 + (Math.max(0, Math.min(100, value)) / 100) * 528;
  }

  yAxis(value: number): number {
    return 308 - (Math.max(0, Math.min(100, value)) / 100) * 272;
  }

  bubbleOpacity(cluster: RiskmapCluster): number {
    return !this.selectedCluster() || this.selectedCluster()?.cluster_id === cluster.cluster_id ? 0.9 : 0.28;
  }

  shortLabel(value: string, maxLength: number): string {
    return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value;
  }

  stageLabel(value: string): string {
    return value.replaceAll('_', ' ');
  }

  onSelectValue(event: Event): string | null {
    return (event.target as HTMLSelectElement).value || null;
  }

  onStageValue(event: Event): LifecycleStage | null {
    return ((event.target as HTMLSelectElement).value as LifecycleStage) || null;
  }

  onBandValue(event: Event): RiskBand | null {
    return ((event.target as HTMLSelectElement).value as RiskBand) || null;
  }

  onSortValue(event: Event): RiskSort {
    return (event.target as HTMLSelectElement).value as RiskSort;
  }

  onCheckboxValue(event: Event): boolean {
    return (event.target as HTMLInputElement).checked;
  }

  colorFor(value: string): string {
    const palette = ['#38bdf8', '#f59e0b', '#34d399', '#f87171', '#818cf8', '#f472b6'];
    const hash = [...value].reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return palette[hash % palette.length];
  }

  private scaleToRange(value: number, min: number, max: number, outMin: number, outMax: number): number {
    if (max === min) {
      return (outMin + outMax) / 2;
    }
    const ratio = (value - min) / (max - min);
    return outMin + Math.max(0, Math.min(1, ratio)) * (outMax - outMin);
  }
}
