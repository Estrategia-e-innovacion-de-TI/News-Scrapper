import {
  AfterViewInit,
  Component,
  ElementRef,
  effect,
  input,
  output,
  signal,
  viewChild,
} from '@angular/core';
import * as d3 from 'd3';

import {
  DARK_THEME,
  LifecycleStage,
  RiskmapCluster,
} from '../../../../../domain/noticias/models';

const WIDTH = 860;
const HEIGHT = 440;
const MARGIN = { top: 42, right: 28, bottom: 82, left: 30 };

const STAGE_ORDER: LifecycleStage[] = [
  'weak_signal',
  'innovation_trigger',
  'rising_attention',
  'peak_visibility',
  'correction',
  'consolidation',
  'productive_adoption',
];

const STAGE_LABELS: Record<LifecycleStage, string> = {
  weak_signal: 'Señal temprana',
  innovation_trigger: 'Aparicion inicial',
  rising_attention: 'Atencion creciente',
  peak_visibility: 'Pico de alerta',
  correction: 'Reduccion / gestion',
  consolidation: 'Consolidacion del riesgo',
  productive_adoption: 'Riesgo persistente',
};

const STAGE_X: Record<LifecycleStage, number> = {
  weak_signal: 0.06,
  innovation_trigger: 0.18,
  rising_attention: 0.34,
  peak_visibility: 0.49,
  correction: 0.64,
  consolidation: 0.79,
  productive_adoption: 0.93,
};

const STAGE_Y: Record<LifecycleStage, number> = {
  weak_signal: 0.2,
  innovation_trigger: 0.33,
  rising_attention: 0.62,
  peak_visibility: 0.92,
  correction: 0.24,
  consolidation: 0.58,
  productive_adoption: 0.68,
};

const CURVE_POINTS: Array<[number, number]> = [
  [0.0, 0.1],
  [0.06, 0.2],
  [0.14, 0.29],
  [0.22, 0.48],
  [0.34, 0.62],
  [0.45, 0.82],
  [0.49, 0.92],
  [0.56, 0.55],
  [0.62, 0.28],
  [0.66, 0.24],
  [0.72, 0.35],
  [0.79, 0.58],
  [0.87, 0.65],
  [0.93, 0.68],
  [1.0, 0.69],
];

interface HypePoint {
  cluster: RiskmapCluster;
  stage: LifecycleStage;
  baseX: number;
  baseY: number;
  x: number;
  y: number;
  radius: number;
  labelLines: string[];
  showLabel: boolean;
}

@Component({
  selector: 'app-riskmap-hype',
  standalone: true,
  template: `
    <div class="rounded-2xl border border-dark-border bg-dark-surface p-5 shadow-sm">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h4 class="text-sm font-semibold text-dark-text">Ciclo de vida del riesgo</h4>
          <p class="mt-1 text-xs leading-5 text-dark-muted">
            Distribucion de clusters de riesgo segun su etapa en el ciclo de vida.
            El tamaño representa el volumen documental y el color la categoria.
          </p>
        </div>
      </div>

      <div class="mt-3 flex flex-wrap gap-2">
        @for (stage of stages; track stage) {
          <button
            class="rounded-full border px-3 py-1 text-xs font-medium transition"
            [class]="stageChipClass(stage)"
            type="button"
            (click)="toggleStage(stage)"
          >
            {{ stageLabel(stage) }}
          </button>
        }
        @if (activeStage()) {
          <button
            class="rounded-full border border-dark-border bg-dark-bg px-3 py-1 text-xs text-dark-muted transition hover:text-dark-text"
            type="button"
            (click)="activeStage.set(null)"
          >
            Ver todos
          </button>
        }
      </div>

      <svg #chart class="mt-4 h-auto w-full" [attr.width]="width" [attr.height]="height"></svg>
    </div>
  `,
})
export class RiskmapHypeComponent implements AfterViewInit {
  readonly clusters = input<RiskmapCluster[]>([]);
  readonly clusterSelected = output<RiskmapCluster>();
  readonly chartRef = viewChild.required<ElementRef<SVGSVGElement>>('chart');

  readonly width = WIDTH;
  readonly height = HEIGHT;
  readonly stages = STAGE_ORDER;
  readonly activeStage = signal<LifecycleStage | null>(null);

  private initialized = false;
  private tooltip: HTMLDivElement | null = null;

  constructor() {
    effect(() => {
      const clusters = this.clusters();
      const active = this.activeStage();
      if (this.initialized) {
        const visible = active ? clusters.filter((c) => c.hype_stage === active) : clusters;
        this.render(visible);
      }
    });
  }

  ngAfterViewInit(): void {
    this.initialized = true;
    this.render(this.clusters());
  }

  toggleStage(stage: LifecycleStage): void {
    this.activeStage.set(this.activeStage() === stage ? null : stage);
  }

  stageLabel(stage: LifecycleStage): string {
    return STAGE_LABELS[stage] ?? stage.replaceAll('_', ' ');
  }

  stageChipClass(stage: LifecycleStage): string {
    const isActive = this.activeStage() === stage;
    const base = 'border ';
    if (isActive) {
      return base + 'border-yellow-500 bg-yellow-400 text-dark-text';
    }
    if (stage === 'weak_signal') return base + 'border-yellow-400 bg-yellow-50 text-yellow-800 hover:bg-yellow-100';
    if (stage === 'peak_visibility') return base + 'border-rose-400 bg-rose-50 text-rose-700 hover:bg-rose-100';
    if (stage === 'correction') return base + 'border-orange-400 bg-orange-50 text-orange-700 hover:bg-orange-100';
    if (stage === 'productive_adoption') return base + 'border-emerald-500 bg-emerald-50 text-emerald-700 hover:bg-emerald-100';
    return base + 'border-dark-border bg-dark-bg text-dark-muted hover:text-dark-text';
  }

  private render(clusters: RiskmapCluster[]): void {
    const svg = d3.select(this.chartRef().nativeElement);
    svg.selectAll('*').remove();

    const plotW = WIDTH - MARGIN.left - MARGIN.right;
    const plotH = HEIGHT - MARGIN.top - MARGIN.bottom;

    svg.append('rect').attr('width', WIDTH).attr('height', HEIGHT).attr('fill', '#ffffff').attr('rx', 12);

    const g = svg.append('g').attr('transform', `translate(${MARGIN.left}, ${MARGIN.top})`);

    // Draw curve
    const lineGen = d3
      .line<[number, number]>()
      .x((d) => d[0] * plotW)
      .y((d) => plotH - d[1] * plotH)
      .curve(d3.curveCatmullRom.alpha(0.5));

    g.append('path')
      .datum(CURVE_POINTS)
      .attr('d', lineGen)
      .attr('fill', 'none')
      .attr('stroke', '#cbd5e1')
      .attr('stroke-width', 2.5)
      .attr('stroke-dasharray', '6,4');

    // Axis labels
    ['Bajo', 'Medio', 'Alto'].forEach((label, i) => {
      g.append('text')
        .attr('x', -8)
        .attr('y', plotH - (i / 2) * plotH)
        .attr('text-anchor', 'end')
        .attr('dominant-baseline', 'middle')
        .attr('fill', DARK_THEME.textMuted)
        .attr('font-size', '10px')
        .text(label);
    });

    g.append('text')
      .attr('x', plotW / 2)
      .attr('y', plotH + 32)
      .attr('text-anchor', 'middle')
      .attr('fill', DARK_THEME.textMuted)
      .attr('font-size', '11px')
      .text('Ciclo de vida del riesgo →');

    g.append('text')
      .attr('x', -MARGIN.left + 12)
      .attr('y', plotH / 2)
      .attr('text-anchor', 'middle')
      .attr('fill', DARK_THEME.textMuted)
      .attr('font-size', '11px')
      .attr('transform', `rotate(-90, ${-MARGIN.left + 12}, ${plotH / 2})`)
      .text('Nivel de alerta →');

    // Stage delimiters
    STAGE_ORDER.forEach((stage) => {
      const stageX = STAGE_X[stage] * plotW;
      g.append('line')
        .attr('x1', stageX).attr('x2', stageX)
        .attr('y1', 0).attr('y2', plotH + 18)
        .attr('stroke', DARK_THEME.border)
        .attr('stroke-dasharray', '3,5')
        .attr('stroke-opacity', 0.5);

      g.append('text')
        .attr('x', stageX)
        .attr('y', plotH + 50)
        .attr('text-anchor', 'middle')
        .attr('fill', DARK_THEME.textMuted)
        .attr('font-size', '9.5px')
        .attr('font-weight', '600')
        .text(STAGE_LABELS[stage]);
    });

    if (clusters.length === 0) return;

    const orderedCategories = [...new Set(clusters.map((c) => c.category))];
    const color = d3.scaleOrdinal<string, string>(d3.schemeTableau10).domain(orderedCategories);

    const r = d3
      .scaleSqrt()
      .domain([0, d3.max(clusters, (c) => c.item_count) ?? 1])
      .range([7, 24]);

    const points: HypePoint[] = clusters.map((cluster) => {
      const stage = cluster.hype_stage ?? 'weak_signal';
      const radius = r(cluster.item_count);
      return {
        cluster,
        stage,
        baseX: STAGE_X[stage] * plotW,
        baseY: plotH - STAGE_Y[stage] * plotH,
        x: STAGE_X[stage] * plotW,
        y: plotH - STAGE_Y[stage] * plotH,
        radius,
        labelLines: [],
        showLabel: false,
      };
    });

    // Force simulation
    const sim = d3
      .forceSimulation(points as any)
      .force('x', d3.forceX<HypePoint>((p) => p.baseX).strength(0.7))
      .force('y', d3.forceY<HypePoint>((p) => p.baseY).strength(0.7))
      .force('collide', d3.forceCollide<HypePoint>((p) => p.radius + 2.5).strength(0.95))
      .stop();

    for (let i = 0; i < 220; i++) sim.tick();

    // Clamp to boundaries
    points.forEach((p) => {
      p.x = Math.max(p.radius + 4, Math.min(plotW - p.radius - 4, (p as any).x));
      p.y = Math.max(p.radius + 4, Math.min(plotH - p.radius - 4, (p as any).y));
    });

    // Smart labels
    const occupiedLabelRects: Array<{ x: number; y: number; w: number; h: number }> = [];
    points.forEach((p) => {
      const label = p.cluster.label.length > 22 ? `${p.cluster.label.slice(0, 22)}...` : p.cluster.label;
      const approxW = label.length * 5.5 + 8;
      const approxH = 14;
      const lx = p.x - approxW / 2;
      const ly = p.y - p.radius - 16;
      const overlaps = occupiedLabelRects.some(
        (r2) => lx < r2.x + r2.w && lx + approxW > r2.x && ly < r2.y + r2.h && ly + approxH > r2.y,
      );
      if (!overlaps && p.radius >= 10) {
        p.labelLines = [label];
        p.showLabel = true;
        occupiedLabelRects.push({ x: lx, y: ly, w: approxW, h: approxH });
      }
    });

    // Draw
    const nodes = g.selectAll('g.hp').data(points).join('g').attr('class', 'hp');

    nodes
      .append('circle')
      .attr('cx', (p) => p.x)
      .attr('cy', (p) => p.y)
      .attr('r', (p) => p.radius)
      .attr('fill', (p) => color(p.cluster.category))
      .attr('fill-opacity', 0.82)
      .attr('stroke', (p) => {
        if (p.cluster.weak_signal_flag) return '#f59e0b';
        if (p.stage === 'peak_visibility') return DARK_THEME.textMuted;
        return color(p.cluster.category);
      })
      .attr('stroke-width', (p) => (p.cluster.weak_signal_flag ? 2.5 : 1.5))
      .attr('stroke-opacity', 0.9)
      .style('cursor', 'pointer')
      .on('mouseenter', (event, p) => { this.showTooltip(p); this.positionTooltip(event); })
      .on('mousemove', (event) => this.positionTooltip(event))
      .on('mouseleave', () => this.hideTooltip())
      .on('click', (_ev, p) => this.clusterSelected.emit(p.cluster));

    nodes
      .filter((p) => p.showLabel)
      .append('text')
      .attr('x', (p) => p.x)
      .attr('y', (p) => p.y - p.radius - 5)
      .attr('text-anchor', 'middle')
      .attr('fill', DARK_THEME.text)
      .attr('font-size', '9.5px')
      .attr('font-weight', '600')
      .attr('pointer-events', 'none')
      .text((p) => p.labelLines[0] ?? '');
  }

  private ensureTooltip(): HTMLDivElement {
    if (this.tooltip) return this.tooltip;
    const t = document.createElement('div');
    t.style.cssText = 'position:fixed;pointer-events:none;z-index:1000;max-width:340px;padding:12px 14px;border-radius:14px;border:1px solid #e2e8f0;background:rgba(255,255,255,0.98);color:#2c2a29;box-shadow:0 18px 40px rgba(15,23,42,.18);font-size:12px;line-height:1.5;opacity:0;transition:opacity 120ms ease;';
    document.body.appendChild(t);
    this.tooltip = t;
    return t;
  }

  private showTooltip(p: HypePoint): void {
    const t = this.ensureTooltip();
    const c = p.cluster;
    const kws = c.top_keywords.slice(0, 4).join(', ');
    t.innerHTML = `
      <div style="font-weight:700;">${this.esc(c.label)}</div>
      <div style="margin-top:2px;color:#64748b;">${this.esc(c.dominant_risk || c.category)} | ${this.esc(STAGE_LABELS[p.stage] ?? p.stage)}</div>
      <div style="margin-top:8px;">Severidad ${c.risk_severity.toFixed(0)} | Persistencia ${c.persistence_score.toFixed(0)} | Dinamica ${c.momentum_score.toFixed(0)}</div>
      <div>Novedad ${c.novelty_score.toFixed(0)} | Documentos ${c.item_count}</div>
      <div style="margin-top:8px;color:#475569;">${this.esc(c.executive_takeaway || c.summary)}</div>
      ${kws ? `<div style="margin-top:8px;color:#64748b;">${this.esc(kws)}</div>` : ''}
    `;
    t.style.opacity = '1';
  }

  private positionTooltip(event: MouseEvent): void {
    const t = this.ensureTooltip();
    const pad = 14;
    const rect = t.getBoundingClientRect();
    const left = Math.min(event.clientX + pad, window.innerWidth - rect.width - pad);
    const top = Math.min(event.clientY + pad, window.innerHeight - rect.height - pad);
    t.style.left = `${Math.max(pad, left)}px`;
    t.style.top = `${Math.max(pad, top)}px`;
  }

  private hideTooltip(): void {
    if (this.tooltip) this.tooltip.style.opacity = '0';
  }

  private esc(value: string): string {
    return value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
  }
}
