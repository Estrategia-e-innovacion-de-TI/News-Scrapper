import { DecimalPipe } from '@angular/common';
import { Component, computed, input, output } from '@angular/core';

import { DARK_THEME, RiskmapCluster } from '../../../../../domain/noticias/models';

@Component({
  selector: 'app-riskmap-impact',
  standalone: true,
  imports: [DecimalPipe],
  template: `
    <div class="space-y-6">
      <section class="rounded-2xl border border-dark-border bg-white p-5 shadow-sm">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h4 class="text-sm font-semibold text-dark-text">Severidad vs momentum</h4>
            <p class="mt-1 text-xs leading-5 text-dark-muted">
              Equivalente de impacto para riesgos: severidad potencial en el eje X,
              momentum en el eje Y y tamano por volumen documental.
            </p>
          </div>
        </div>
        <svg viewBox="0 0 620 360" class="mt-4 h-auto w-full">
          <rect width="620" height="360" fill="#ffffff" rx="14" />
          <rect x="56" y="36" width="264" height="136" fill="#fff7ed" />
          <rect x="320" y="36" width="264" height="136" fill="#fee2e2" />
          <rect x="56" y="172" width="264" height="136" fill="#f8fafc" />
          <rect x="320" y="172" width="264" height="136" fill="#fef9c3" />
          @for (tick of axisTicks; track tick) {
            <line [attr.x1]="scatterX(tick)" [attr.x2]="scatterX(tick)" y1="36" y2="308" [attr.stroke]="theme.border" stroke-dasharray="4 6" />
            <line x1="56" x2="584" [attr.y1]="scatterY(tick)" [attr.y2]="scatterY(tick)" [attr.stroke]="theme.border" stroke-dasharray="4 6" />
            <text [attr.x]="scatterX(tick)" y="326" text-anchor="middle" [attr.fill]="theme.textMuted" font-size="10">{{ tick }}</text>
            <text x="44" [attr.y]="scatterY(tick) + 4" text-anchor="end" [attr.fill]="theme.textMuted" font-size="10">{{ tick }}</text>
          }
          <line x1="56" y1="308" x2="584" y2="308" [attr.stroke]="theme.border" />
          <line x1="56" y1="36" x2="56" y2="308" [attr.stroke]="theme.border" />
          <text x="320" y="344" text-anchor="middle" [attr.fill]="theme.textMuted" font-size="11">Severidad potencial</text>
          <text x="18" y="182" text-anchor="middle" [attr.fill]="theme.textMuted" font-size="11" transform="rotate(-90 18 182)">Momentum</text>
          <text x="72" y="58" fill="#2c2a29" font-size="12" font-weight="600">Investigar</text>
          <text x="336" y="58" fill="#2c2a29" font-size="12" font-weight="600">Priorizar</text>
          <text x="72" y="194" fill="#64748b" font-size="12" font-weight="600">Observar</text>
          <text x="336" y="194" fill="#64748b" font-size="12" font-weight="600">Monitorear</text>
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
                <title>{{ point.cluster.label }}&#10;Severidad: {{ point.cluster.risk_severity | number:'1.0-0' }}&#10;Momentum: {{ point.cluster.momentum_score | number:'1.0-0' }}&#10;Persistencia: {{ point.cluster.persistence_score | number:'1.0-0' }}&#10;Impacto: {{ point.cluster.impact_score | number:'1.0-0' }}</title>
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

      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div class="rounded-2xl border border-dark-border bg-dark-surface p-4">
          <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Severidad</p>
          <p class="mt-2 text-sm leading-6 text-dark-text/90">Equivale al impacto potencial del riesgo sobre la organizacion.</p>
        </div>
        <div class="rounded-2xl border border-dark-border bg-dark-surface p-4">
          <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Momentum</p>
          <p class="mt-2 text-sm leading-6 text-dark-text/90">Velocidad de aparicion y aceleracion documental reciente.</p>
        </div>
        <div class="rounded-2xl border border-dark-border bg-dark-surface p-4">
          <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Persistencia</p>
          <p class="mt-2 text-sm leading-6 text-dark-text/90">Recurrencia temporal y estabilidad de la senal en la ventana.</p>
        </div>
        <div class="rounded-2xl border border-dark-border bg-dark-surface p-4">
          <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Novedad</p>
          <p class="mt-2 text-sm leading-6 text-dark-text/90">Senal temprana o emergente que puede no tener gran volumen aun.</p>
        </div>
      </div>
    </div>
  `,
})
export class RiskmapImpactComponent {
  readonly clusters = input.required<RiskmapCluster[]>();
  readonly selectedCluster = input<RiskmapCluster | null>(null);
  readonly clusterSelected = output<RiskmapCluster>();

  readonly theme = DARK_THEME;
  readonly axisTicks = [0, 25, 50, 75, 100];

  readonly points = computed(() => {
    const items = this.clusters();
    const maxCount = Math.max(...items.map((cluster) => cluster.item_count), 1);
    return items.map((cluster) => ({
      cluster,
      x: this.scatterX(cluster.risk_severity),
      y: this.scatterY(cluster.momentum_score),
      r: 8 + (cluster.item_count / maxCount) * 18,
      color: this.colorFor(cluster.category),
    }));
  });

  scatterX(value: number): number {
    return 56 + (Math.max(0, Math.min(100, value)) / 100) * 528;
  }

  scatterY(value: number): number {
    return 308 - (Math.max(0, Math.min(100, value)) / 100) * 272;
  }

  bubbleOpacity(cluster: RiskmapCluster): number {
    return !this.selectedCluster() || this.selectedCluster()?.cluster_id === cluster.cluster_id ? 0.9 : 0.28;
  }

  shortLabel(value: string, maxLength: number): string {
    return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value;
  }

  colorFor(value: string): string {
    const palette = ['#38bdf8', '#f59e0b', '#34d399', '#f87171', '#818cf8', '#f472b6'];
    const hash = [...value].reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return palette[hash % palette.length];
  }
}
