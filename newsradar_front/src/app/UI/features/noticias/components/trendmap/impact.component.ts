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

import {
  DARK_THEME,
  TrendmapCluster,
} from '../../../../../domain/noticias/models';

const WIDTH = 1060;
const HEIGHT = 1180;
const MARGIN = { top: 34, right: 28, bottom: 34, left: 28 };

type StrategicStage =
  | 'Descubrir'
  | 'Explorar'
  | 'Conceptualizar'
  | 'Probar PoC'
  | 'Pilotear'
  | 'Refinar'
  | 'Viabilizar o desechar'
  | 'Habilitar';

const STRATEGIC_STAGES: StrategicStage[] = [
  'Descubrir',
  'Explorar',
  'Conceptualizar',
  'Probar PoC',
  'Pilotear',
  'Refinar',
  'Viabilizar o desechar',
  'Habilitar',
];

const STRATEGIC_STAGE_COLORS: Record<StrategicStage, string> = {
  'Descubrir': '#f59e0b',
  'Explorar': '#f97316',
  'Conceptualizar': '#0ea5e9',
  'Probar PoC': '#6366f1',
  'Pilotear': '#22c55e',
  'Refinar': '#14b8a6',
  'Viabilizar o desechar': '#e11d48',
  'Habilitar': '#10b981',
};

interface StageDecision {
  stage: StrategicStage;
  reason: string;
  rule: string;
}

interface PositionedPoint {
  cluster: TrendmapCluster;
  stage: StrategicStage;
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
  selector: 'app-trendmap-impact',
  standalone: true,
  template: `
    <div class="rounded-2xl border border-dark-border bg-white p-5 shadow-sm">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h4 class="text-sm font-semibold text-dark-text">Mapa por etapa estrategica</h4>
          <p class="mt-1 text-xs leading-5 text-dark-muted">
            Visualizacion por franjas: cada etapa se muestra en una fila y sus clusters se ordenan
            horizontalmente de mayor a menor impacto. Pasa el cursor para ver por que cada cluster cae en su etapa.
          </p>
          <p class="mt-1 text-xs leading-5 text-dark-muted">
            Color de relleno = categoria. Borde y franja = etapa estrategica.
          </p>
        </div>
      </div>
      <svg #chart class="mt-4 h-auto w-full max-w-full" [attr.width]="width" [attr.height]="height"></svg>
    </div>
  `,
})
export class TrendmapImpactComponent implements AfterViewInit, OnDestroy {
  readonly clusters = input<TrendmapCluster[]>([]);
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

  private render(clusters: TrendmapCluster[]): void {
    const svg = d3.select(this.chartRef().nativeElement);
    svg.selectAll('*').remove();
    svg
      .attr('width', '100%')
      .attr('height', HEIGHT)
      .attr('viewBox', `0 0 ${WIDTH} ${HEIGHT}`)
      .attr('preserveAspectRatio', 'xMidYMid meet');

    if (clusters.length === 0) {
      return;
    }

    const r = d3
      .scaleSqrt()
      .domain([0, d3.max(clusters, (cluster) => cluster.item_count) ?? 1])
      .range([10, 30]);

    svg
      .append('rect')
      .attr('width', WIDTH)
      .attr('height', HEIGHT)
      .attr('fill', '#ffffff')
      .attr('rx', 12);

    const decisions = clusters.map((cluster) => ({
      cluster,
      decision: this.strategicStageDecision(cluster),
    }));

    // Keep category colors fully aligned with UMAP's d3 ordinal mapping.
    const orderedCategories = [...new Set(clusters.map((cluster) => cluster.category))];
    const categoryColor = d3.scaleOrdinal<string, string>(d3.schemeTableau10).domain(orderedCategories);

    const pointsByStage = new Map<StrategicStage, Array<{ cluster: TrendmapCluster; decision: StageDecision }>>();
    STRATEGIC_STAGES.forEach((stage) => pointsByStage.set(stage, []));
    decisions.forEach((item) => {
      pointsByStage.get(item.decision.stage)?.push(item);
    });

    const laneGap = 12;
    const laneHeight = (HEIGHT - MARGIN.top - MARGIN.bottom - laneGap * (STRATEGIC_STAGES.length - 1)) / STRATEGIC_STAGES.length;
    const laneLeft = MARGIN.left + 210;
    const laneRight = WIDTH - MARGIN.right - 20;

    const positionedPoints: PositionedPoint[] = [];

    STRATEGIC_STAGES.forEach((stage, index) => {
      const laneTop = MARGIN.top + index * (laneHeight + laneGap);
      const laneBottom = laneTop + laneHeight;
      const laneCenterY = laneTop + laneHeight / 2;
      const laneColor = STRATEGIC_STAGE_COLORS[stage];
      const group = (pointsByStage.get(stage) ?? []).sort(
        (a, b) =>
          b.cluster.impact_score - a.cluster.impact_score
          || b.cluster.momentum_score - a.cluster.momentum_score
          || b.cluster.item_count - a.cluster.item_count,
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
        .text('Mayor impacto');

      svg
        .append('text')
        .attr('x', laneRight)
        .attr('y', laneTop + laneHeight - 8)
        .attr('fill', DARK_THEME.textMuted)
        .attr('font-size', '11px')
        .attr('font-weight', '600')
        .attr('text-anchor', 'end')
        .text('Menor impacto');

      svg
        .append('circle')
        .attr('cx', MARGIN.left + 16)
        .attr('cy', laneTop + 18)
        .attr('r', 6)
        .attr('fill', laneColor);

      svg
        .append('text')
        .attr('x', MARGIN.left + 30)
        .attr('y', laneTop + 22)
        .attr('fill', DARK_THEME.text)
        .attr('font-size', stage === 'Viabilizar o desechar' ? '13px' : '14px')
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
      const requiredWidth =
        rawRadii.reduce((sum, radius) => sum + radius * 2, 0) + Math.max(0, group.length - 1) * gap;
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
        const label =
          point.cluster.label.length > maxChars
            ? `${point.cluster.label.slice(0, maxChars)}...`
            : point.cluster.label;
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
      .text('Orden horizontal por impacto y etiquetas inteligentes sin solape');

    const bubbles = svg
      .append('g')
      .selectAll('g.cluster')
      .data(positionedPoints)
      .join('g')
      .attr('class', 'cluster');

    bubbles
      .append('circle')
      .attr('cx', (point) => point.x)
      .attr('cy', (point) => point.y)
      .attr('r', (point) => point.radius)
      .attr('fill', (point) => categoryColor(point.cluster.category))
      .attr('fill-opacity', 0.82)
      .attr('stroke', (point) => STRATEGIC_STAGE_COLORS[point.stage])
      .attr('stroke-opacity', 0.95)
      .attr('stroke-width', 2.2)
      .style('cursor', 'pointer')
      .on('mouseenter', (event, point) => {
        this.showClusterTooltip(point);
        this.positionTooltip(event);
      })
      .on('mousemove', (event) => {
        this.positionTooltip(event);
      })
      .on('mouseleave', () => {
        this.hideTooltip();
      });

    bubbles
      .filter((point) => point.showLabel)
      .append('line')
      .attr('x1', (point) => point.x)
      .attr('x2', (point) => point.labelX)
      .attr('y1', (point) => point.y - point.radius - 2)
      .attr('y2', (point) => point.labelY + 3)
      .attr('stroke', DARK_THEME.border)
      .attr('stroke-opacity', 0.7)
      .attr('stroke-width', 0.8)
      .attr('pointer-events', 'none');

    bubbles
      .filter((point) => point.showLabel)
      .append('text')
      .attr('x', (point) => point.labelX)
      .attr('y', (point) => point.labelY)
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'middle')
      .attr('fill', DARK_THEME.text)
      .attr('font-size', '11px')
      .attr('font-weight', '600')
      .attr('pointer-events', 'none')
      .text((point) => point.label);
  }

  private ensureTooltip(): HTMLDivElement {
    if (this.tooltip) {
      return this.tooltip;
    }
    const tooltip = document.createElement('div');
    tooltip.style.position = 'fixed';
    tooltip.style.pointerEvents = 'none';
    tooltip.style.zIndex = '1000';
    tooltip.style.maxWidth = '340px';
    tooltip.style.padding = '12px 14px';
    tooltip.style.borderRadius = '14px';
    tooltip.style.border = '1px solid #e2e8f0';
    tooltip.style.background = 'rgba(255, 255, 255, 0.98)';
    tooltip.style.color = '#2c2a29';
    tooltip.style.boxShadow = '0 18px 40px rgba(15, 23, 42, 0.18)';
    tooltip.style.fontSize = '12px';
    tooltip.style.lineHeight = '1.5';
    tooltip.style.opacity = '0';
    tooltip.style.transition = 'opacity 120ms ease';
    document.body.appendChild(tooltip);
    this.tooltip = tooltip;
    return tooltip;
  }

  private showClusterTooltip(point: PositionedPoint): void {
    const tooltip = this.ensureTooltip();
    const cluster = point.cluster;
    const keywords = cluster.top_keywords.slice(0, 4).join(', ');
    tooltip.innerHTML = `
      <div style="font-weight:700; color:#2c2a29;">${this.escapeHtml(cluster.label)}</div>
      <div style="margin-top:2px; color:#64748b;">${this.escapeHtml(cluster.category)} | ${this.escapeHtml(point.stage)}</div>
      <div style="margin-top:8px;">Impacto ${cluster.impact_score.toFixed(0)} | Madurez ${cluster.maturity_score.toFixed(0)} | Dinamica ${cluster.momentum_score.toFixed(0)}</div>
      <div>Documentos ${cluster.item_count} | Calidad ${cluster.cluster_quality.score.toFixed(0)} | Novedad ${cluster.novelty_score.toFixed(0)}</div>
      <div style="margin-top:8px; color:#334155;"><strong>Por que cae en esta etapa:</strong> ${this.escapeHtml(point.reason)}</div>
      <div style="margin-top:4px; color:#64748b; font-size:13px;">${this.escapeHtml(point.rule)}</div>
      <div style="margin-top:8px; color:#475569;">${this.escapeHtml(cluster.executive_takeaway || cluster.summary)}</div>
      <div style="margin-top:8px; color:#64748b;">${this.escapeHtml(keywords)}</div>
    `;
    tooltip.style.opacity = '1';
  }

  private positionTooltip(event: MouseEvent): void {
    const tooltip = this.ensureTooltip();
    const padding = 14;
    const rect = tooltip.getBoundingClientRect();
    const left = Math.min(
      event.clientX + padding,
      window.innerWidth - rect.width - padding,
    );
    const top = Math.min(
      event.clientY + padding,
      window.innerHeight - rect.height - padding,
    );
    tooltip.style.left = `${Math.max(padding, left)}px`;
    tooltip.style.top = `${Math.max(padding, top)}px`;
  }

  private hideTooltip(): void {
    if (this.tooltip) {
      this.tooltip.style.opacity = '0';
    }
  }

  private escapeHtml(value: string): string {
    return value
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  private strategicStageDecision(cluster: TrendmapCluster): StageDecision {
    const impact = cluster.impact_score;
    const maturity = cluster.maturity_score;
    const novelty = cluster.novelty_score;
    const momentum = cluster.momentum_score;

    if (novelty >= 80 && maturity < 30) {
      return {
        stage: 'Descubrir',
        reason: 'Alta novedad con madurez baja: requiere descubrimiento inicial.',
        rule: 'Regla: novedad >= 80 y madurez < 30.',
      };
    }
    if (novelty >= 65 && maturity < 45) {
      return {
        stage: 'Explorar',
        reason: 'Novedad relevante en una fase temprana de madurez.',
        rule: 'Regla: novedad >= 65 y madurez < 45.',
      };
    }
    if (impact >= 45 && maturity < 55) {
      return {
        stage: 'Conceptualizar',
        reason: 'Impacto potencial suficiente pero todavia sin madurez alta.',
        rule: 'Regla: impacto >= 45 y madurez < 55.',
      };
    }
    if (impact >= 55 && maturity < 65) {
      return {
        stage: 'Probar PoC',
        reason: 'Impacto alto con madurez intermedia: apto para prueba controlada.',
        rule: 'Regla: impacto >= 55 y madurez < 65.',
      };
    }
    if (impact >= 60 && maturity < 75 && momentum >= 45) {
      return {
        stage: 'Pilotear',
        reason: 'Impacto y dinamica suficientemente altos para piloto.',
        rule: 'Regla: impacto >= 60, madurez < 75 y dinamica >= 45.',
      };
    }
    if (maturity >= 60 && maturity < 85 && momentum >= 40) {
      return {
        stage: 'Refinar',
        reason: 'Madurez en consolidacion con dinamica activa para ajuste fino.',
        rule: 'Regla: madurez >= 60, madurez < 85 y dinamica >= 40.',
      };
    }
    if (impact < 45 && maturity >= 70) {
      return {
        stage: 'Viabilizar o desechar',
        reason: 'Alta madurez con bajo impacto: se evalua viabilidad o descarte.',
        rule: 'Regla: impacto < 45 y madurez >= 70.',
      };
    }

    return {
      stage: 'Habilitar',
      reason: 'Senal madura y lista para incorporacion operativa.',
      rule: 'Regla por defecto cuando no aplica una condicion previa.',
    };
  }

  private mapStrategicStage(cluster: TrendmapCluster): StrategicStage {
    return this.strategicStageDecision(cluster).stage;
  }

  private computeReadiness(cluster: TrendmapCluster): number {
    const maturity = cluster.maturity_score;
    const impact = cluster.impact_score;
    const noveltyInversion = 100 - cluster.novelty_score;
    const momentum = cluster.momentum_score;
    return Math.max(
      0,
      Math.min(100, maturity * 0.45 + impact * 0.25 + noveltyInversion * 0.2 + momentum * 0.1),
    );
  }
}
