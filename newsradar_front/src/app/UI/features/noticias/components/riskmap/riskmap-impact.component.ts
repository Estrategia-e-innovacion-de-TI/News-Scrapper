import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  effect,
  input,
  viewChild,
} from '@angular/core';
import * as d3 from 'd3';

import { DARK_THEME, RiskmapCluster } from '../../../../../domain/noticias/models';

const WIDTH = 1060;
const HEIGHT = 1180;
const MARGIN = { top: 34, right: 28, bottom: 34, left: 28 };

type RiskStage =
  | 'Señal temprana'
  | 'Emergente'
  | 'En escalada'
  | 'Critico'
  | 'En gestion activa'
  | 'Mitigado'
  | 'Monitoreo'
  | 'Residual';

const RISK_STAGES: RiskStage[] = [
  'Critico',
  'En escalada',
  'En gestion activa',
  'Emergente',
  'Señal temprana',
  'Monitoreo',
  'Mitigado',
  'Residual',
];

const RISK_STAGE_COLORS: Record<RiskStage, string> = {
  Critico: '#e11d48',
  'En escalada': '#f97316',
  'En gestion activa': '#f59e0b',
  Emergente: '#0ea5e9',
  'Señal temprana': '#6366f1',
  Monitoreo: '#22c55e',
  Mitigado: '#14b8a6',
  Residual: '#64748b',
};

interface RiskStageDecision {
  stage: RiskStage;
  reason: string;
  rule: string;
}

interface PositionedPoint {
  cluster: RiskmapCluster;
  stage: RiskStage;
  reason: string;
  rule: string;
  x: number;
  y: number;
  radius: number;
  label: string;
  labelX: number;
  labelY: number;
  showLabel: boolean;
}

@Component({
  selector: 'app-riskmap-impact',
  standalone: true,
  template: `
    <div class="rounded-2xl border border-dark-border bg-white p-5 shadow-sm">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h4 class="text-sm font-semibold text-dark-text">Mapa por etapa de riesgo</h4>
          <p class="mt-1 text-xs leading-5 text-dark-muted">
            Visualizacion por franjas segun urgencia del riesgo: cada etapa muestra los clusters ordenados por severidad.
          </p>
          <p class="mt-1 text-xs leading-5 text-dark-muted">
            Color del relleno = categoria de riesgo. Borde y franja = etapa de urgencia.
          </p>
        </div>
      </div>
      <svg #chart class="mt-4 h-auto w-full max-w-full" [attr.width]="width" [attr.height]="height"></svg>
    </div>
  `,
})
export class RiskmapImpactComponent implements AfterViewInit, OnDestroy {
  readonly clusters = input<RiskmapCluster[]>([]);
  readonly chartRef = viewChild.required<ElementRef<SVGSVGElement>>('chart');

  readonly width = WIDTH;
  readonly height = HEIGHT;

  private initialized = false;
  private tooltip: HTMLDivElement | null = null;

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

  ngOnDestroy(): void {
    this.tooltip?.remove();
    this.tooltip = null;
  }

  private render(clusters: RiskmapCluster[]): void {
    const svg = d3.select(this.chartRef().nativeElement);
    svg.selectAll('*').remove();
    svg
      .attr('width', '100%')
      .attr('height', HEIGHT)
      .attr('viewBox', `0 0 ${WIDTH} ${HEIGHT}`)
      .attr('preserveAspectRatio', 'xMidYMid meet');

    if (clusters.length === 0) return;

    const r = d3
      .scaleSqrt()
      .domain([0, d3.max(clusters, (c) => c.item_count) ?? 1])
      .range([10, 30]);

    svg.append('rect').attr('width', WIDTH).attr('height', HEIGHT).attr('fill', '#ffffff').attr('rx', 12);

    const decisions = clusters.map((cluster) => ({
      cluster,
      decision: this.riskStageDecision(cluster),
    }));

    const orderedCategories = [...new Set(clusters.map((c) => c.category))];
    const categoryColor = d3.scaleOrdinal<string, string>(d3.schemeTableau10).domain(orderedCategories);

    const pointsByStage = new Map<RiskStage, Array<{ cluster: RiskmapCluster; decision: RiskStageDecision }>>();
    RISK_STAGES.forEach((stage) => pointsByStage.set(stage, []));
    decisions.forEach((item) => pointsByStage.get(item.decision.stage)?.push(item));

    const laneGap = 12;
    const laneHeight = (HEIGHT - MARGIN.top - MARGIN.bottom - laneGap * (RISK_STAGES.length - 1)) / RISK_STAGES.length;
    const laneLeft = MARGIN.left + 210;
    const laneRight = WIDTH - MARGIN.right - 20;

    const positionedPoints: PositionedPoint[] = [];

    RISK_STAGES.forEach((stage, index) => {
      const laneTop = MARGIN.top + index * (laneHeight + laneGap);
      const laneCenterY = laneTop + laneHeight / 2;
      const laneColor = RISK_STAGE_COLORS[stage];
      const group = (pointsByStage.get(stage) ?? []).sort(
        (a, b) => b.cluster.risk_severity - a.cluster.risk_severity || b.cluster.persistence_score - a.cluster.persistence_score,
      );

      svg
        .append('rect')
        .attr('x', MARGIN.left)
        .attr('y', laneTop)
        .attr('width', WIDTH - MARGIN.left - MARGIN.right)
        .attr('height', laneHeight)
        .attr('rx', 10)
        .attr('fill', laneColor)
        .attr('fill-opacity', 0.08)
        .attr('stroke', DARK_THEME.border)
        .attr('stroke-opacity', 0.7)
        .attr('stroke-width', 1);

      svg
        .append('line')
        .attr('x1', laneLeft)
        .attr('x2', laneRight)
        .attr('y1', laneCenterY)
        .attr('y2', laneCenterY)
        .attr('stroke', DARK_THEME.border)
        .attr('stroke-dasharray', '4,6')
        .attr('stroke-opacity', 0.7);

      svg
        .append('text')
        .attr('x', laneLeft)
        .attr('y', laneTop + laneHeight - 8)
        .attr('fill', DARK_THEME.textMuted)
        .attr('font-size', '11px')
        .attr('font-weight', '600')
        .text('Mayor severidad');

      svg
        .append('text')
        .attr('x', laneRight)
        .attr('y', laneTop + laneHeight - 8)
        .attr('fill', DARK_THEME.textMuted)
        .attr('font-size', '11px')
        .attr('font-weight', '600')
        .attr('text-anchor', 'end')
        .text('Menor severidad');

      svg.append('circle').attr('cx', MARGIN.left + 16).attr('cy', laneTop + 18).attr('r', 6).attr('fill', laneColor);

      svg
        .append('text')
        .attr('x', MARGIN.left + 30)
        .attr('y', laneTop + 22)
        .attr('fill', DARK_THEME.text)
        .attr('font-size', '14px')
        .attr('font-weight', '700')
        .text(stage);

      svg
        .append('text')
        .attr('x', MARGIN.left + 30)
        .attr('y', laneTop + 40)
        .attr('fill', DARK_THEME.textMuted)
        .attr('font-size', '12px')
        .text(`${group.length} clusters`);

      const left = laneLeft + 18;
      const right = laneRight - 14;
      const gap = 6;
      const rawRadii = group.map((item) => r(item.cluster.item_count));
      const availableWidth = right - left;
      const requiredWidth = rawRadii.reduce((sum, radius) => sum + radius * 2, 0) + Math.max(0, group.length - 1) * gap;
      const radiusScale = requiredWidth > 0 ? Math.min(1, availableWidth / requiredWidth) : 1;
      const radii = rawRadii.map((radius) => Math.max(4.5, radius * radiusScale));

      const stagePoints: PositionedPoint[] = [];
      let cursorX = left;
      group.forEach((item, idx) => {
        const radius = radii[idx];
        const pointX = cursorX + radius;
        cursorX = pointX + radius + gap;
        stagePoints.push({
          cluster: item.cluster,
          stage,
          reason: item.decision.reason,
          rule: item.decision.rule,
          x: Math.max(left + radius, Math.min(right - radius, pointX)),
          y: laneCenterY,
          radius,
          label: '',
          labelX: 0,
          labelY: 0,
          showLabel: false,
        });
      });

      let lastLabelEnd = left;
      stagePoints.forEach((point) => {
        const maxChars = point.radius >= 18 ? 24 : 18;
        const label = point.cluster.label.length > maxChars ? `${point.cluster.label.slice(0, maxChars)}...` : point.cluster.label;
        const approxWidth = label.length * 5.2;
        const labelStart = point.x - approxWidth / 2;
        const labelEnd = point.x + approxWidth / 2;
        const hasSpace = point.radius >= 11 && labelStart > lastLabelEnd + 8 && labelEnd < right;
        if (hasSpace) {
          point.label = label;
          point.labelX = point.x;
          point.labelY = laneTop + 14;
          point.showLabel = true;
          lastLabelEnd = labelEnd;
        }
      });

      positionedPoints.push(...stagePoints);
    });

    svg
      .append('text')
      .attr('x', laneLeft)
      .attr('y', HEIGHT - 12)
      .attr('fill', DARK_THEME.textMuted)
      .attr('font-size', '12px')
      .text('Orden horizontal por severidad y persistencia, con etiquetas sin solape');

    const bubbles = svg.append('g').selectAll('g.riskcluster').data(positionedPoints).join('g').attr('class', 'riskcluster');

    bubbles
      .append('circle')
      .attr('cx', (p) => p.x)
      .attr('cy', (p) => p.y)
      .attr('r', (p) => p.radius)
      .attr('fill', (p) => categoryColor(p.cluster.category))
      .attr('fill-opacity', 0.82)
      .attr('stroke', (p) => RISK_STAGE_COLORS[p.stage])
      .attr('stroke-opacity', 0.95)
      .attr('stroke-width', 2.2)
      .style('cursor', 'pointer')
      .on('mouseenter', (event, p) => {
        this.showClusterTooltip(p);
        this.positionTooltip(event);
      })
      .on('mousemove', (event) => this.positionTooltip(event))
      .on('mouseleave', () => this.hideTooltip());

    bubbles
      .filter((p) => p.showLabel)
      .append('line')
      .attr('x1', (p) => p.x)
      .attr('x2', (p) => p.labelX)
      .attr('y1', (p) => p.y - p.radius - 2)
      .attr('y2', (p) => p.labelY + 3)
      .attr('stroke', DARK_THEME.border)
      .attr('stroke-opacity', 0.7)
      .attr('stroke-width', 0.8)
      .attr('pointer-events', 'none');

    bubbles
      .filter((p) => p.showLabel)
      .append('text')
      .attr('x', (p) => p.labelX)
      .attr('y', (p) => p.labelY)
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'middle')
      .attr('fill', DARK_THEME.text)
      .attr('font-size', '11px')
      .attr('font-weight', '600')
      .attr('pointer-events', 'none')
      .text((p) => p.label);
  }

  private riskStageDecision(cluster: RiskmapCluster): RiskStageDecision {
    const severity = cluster.risk_severity;
    const persistence = cluster.persistence_score;
    const novelty = cluster.novelty_score;
    const momentum = cluster.momentum_score;

    if (severity >= 75 && persistence >= 65) {
      return {
        stage: 'Critico',
        reason: 'Severidad y persistencia muy altas: accion inmediata requerida.',
        rule: 'Regla: severidad >= 75 y persistencia >= 65.',
      };
    }
    if (severity >= 60 && momentum >= 60) {
      return {
        stage: 'En escalada',
        reason: 'Riesgo de alta severidad con dinamica creciente activa.',
        rule: 'Regla: severidad >= 60 y dinamica >= 60.',
      };
    }
    if (severity >= 65 && momentum < 45) {
      return {
        stage: 'En gestion activa',
        reason: 'Alta severidad con dinamica estabilizada: bajo gestion.',
        rule: 'Regla: severidad >= 65 y dinamica < 45.',
      };
    }
    if (novelty >= 70 && severity < 50) {
      return {
        stage: 'Señal temprana',
        reason: 'Alta novedad con severidad aun baja: señal emergente.',
        rule: 'Regla: novedad >= 70 y severidad < 50.',
      };
    }
    if (severity >= 40 && severity < 65 && momentum >= 45) {
      return {
        stage: 'Emergente',
        reason: 'Severidad media con dinamica activa: en curva de crecimiento.',
        rule: 'Regla: severidad 40-65 y dinamica >= 45.',
      };
    }
    if (severity >= 35 && severity < 65 && momentum < 40) {
      return {
        stage: 'Monitoreo',
        reason: 'Severidad moderada con baja dinamica: requiere seguimiento.',
        rule: 'Regla: severidad 35-65 y dinamica < 40.',
      };
    }
    if (persistence < 40 && severity >= 40) {
      return {
        stage: 'Mitigado',
        reason: 'Persistencia baja: la señal ha perdido fuerza tras intervencion.',
        rule: 'Regla: persistencia < 40 y severidad >= 40.',
      };
    }
    return {
      stage: 'Residual',
      reason: 'Señal debil y estable: bajo nivel de urgencia.',
      rule: 'Regla por defecto para señales de bajo impacto.',
    };
  }

  private ensureTooltip(): HTMLDivElement {
    if (this.tooltip) return this.tooltip;
    const tooltip = document.createElement('div');
    tooltip.style.cssText = 'position:fixed;pointer-events:none;z-index:1000;max-width:340px;padding:12px 14px;border-radius:14px;border:1px solid #e2e8f0;background:rgba(255,255,255,0.98);color:#2c2a29;box-shadow:0 18px 40px rgba(15,23,42,.18);font-size:12px;line-height:1.5;opacity:0;transition:opacity 120ms ease;';
    document.body.appendChild(tooltip);
    this.tooltip = tooltip;
    return tooltip;
  }

  private showClusterTooltip(point: PositionedPoint): void {
    const t = this.ensureTooltip();
    const c = point.cluster;
    t.innerHTML = `
      <div style="font-weight:700;">${this.esc(c.label)}</div>
      <div style="margin-top:2px;color:#64748b;">${this.esc(c.dominant_risk || c.category)} | ${this.esc(point.stage)}</div>
      <div style="margin-top:8px;">Severidad ${c.risk_severity.toFixed(0)} | Persistencia ${c.persistence_score.toFixed(0)} | Dinamica ${c.momentum_score.toFixed(0)}</div>
      <div>Documentos ${c.item_count} | Novedad ${c.novelty_score.toFixed(0)}</div>
      <div style="margin-top:8px;color:#334155;"><strong>Por que en esta etapa:</strong> ${this.esc(point.reason)}</div>
      <div style="margin-top:4px;color:#64748b;">${this.esc(point.rule)}</div>
      <div style="margin-top:8px;color:#475569;">${this.esc(c.executive_takeaway || c.summary)}</div>
    `;
    t.style.opacity = '1';
  }

  private positionTooltip(event: MouseEvent): void {
    const t = this.ensureTooltip();
    const padding = 14;
    const rect = t.getBoundingClientRect();
    const left = Math.min(event.clientX + padding, window.innerWidth - rect.width - padding);
    const top = Math.min(event.clientY + padding, window.innerHeight - rect.height - padding);
    t.style.left = `${Math.max(padding, left)}px`;
    t.style.top = `${Math.max(padding, top)}px`;
  }

  private hideTooltip(): void {
    if (this.tooltip) this.tooltip.style.opacity = '0';
  }

  private esc(value: string): string {
    return value
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }
}
