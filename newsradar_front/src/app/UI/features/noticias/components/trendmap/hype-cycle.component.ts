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
  TrendmapCluster,
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
  innovation_trigger: 'Disparador de innovacion',
  rising_attention: 'Atencion creciente',
  peak_visibility: 'Pico de visibilidad',
  correction: 'Correccion',
  consolidation: 'Consolidacion',
  productive_adoption: 'Adopcion productiva',
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

interface HypePoint {
  cluster: TrendmapCluster;
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
  selector: 'app-hype-cycle',
  standalone: true,
  template: `
    <div class="rounded-2xl border border-dark-border bg-dark-surface p-5 shadow-sm">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h4 class="text-sm font-semibold text-dark-text">Hype cycle operativo</h4>
          <p class="mt-1 text-xs leading-5 text-dark-muted">
            La etapa se deriva de madurez, impacto, dinamica, novedad e incertidumbre. Pasa el cursor
            sobre una etapa o burbuja para ver el detalle; la grafica separa burbujas automaticamente y muestra
            etiquetas solo donde hay espacio suficiente.
          </p>
        </div>
        <button
          class="rounded-full border border-dark-border bg-white px-3 py-1 text-xs font-medium text-dark-muted transition hover:border-yellow-400 hover:text-dark-text"
          type="button"
          (click)="toggleStage(null)"
        >
          Ver todas
        </button>
      </div>

      <div class="mt-4 flex flex-wrap gap-2">
        @for (stage of stageOrder; track stage) {
          <button
            class="rounded-full border px-3 py-1.5 text-xs transition"
            [class]="stageChipClass(stage)"
            type="button"
            (click)="toggleStage(stage)"
          >
            {{ stageLabel(stage) }}
            <span class="ml-2 rounded-full bg-white px-2 py-0.5 text-[10px] text-dark-muted">
              {{ stageCount(stage) }}
            </span>
          </button>
        }
      </div>

      <svg #chart class="mt-4 w-full max-w-full" [attr.width]="width" [attr.height]="height"></svg>
    </div>
  `,
})
export class HypeCycleComponent implements AfterViewInit {
  readonly clusters = input<TrendmapCluster[]>([]);
  readonly chartRef = viewChild.required<ElementRef<SVGSVGElement>>('chart');

  readonly clusterSelected = output<TrendmapCluster | null>();

  readonly width = WIDTH;
  readonly height = HEIGHT;
  readonly stageOrder = STAGE_ORDER;
  readonly activeStage = signal<LifecycleStage | null>(null);

  private initialized = false;
  private tooltip: HTMLDivElement | null = null;

  constructor() {
    effect(() => {
      this.activeStage();
      if (this.initialized) {
        this.render(this.clusters());
      }
    });
  }

  ngAfterViewInit(): void {
    this.initialized = true;
    this.render(this.clusters());
  }

  stageLabel(stage: LifecycleStage): string {
    return STAGE_LABELS[stage];
  }

  stageCount(stage: LifecycleStage): number {
    return this.clusters().filter((cluster) => cluster.hype_stage === stage).length;
  }

  stageChipClass(stage: LifecycleStage): string {
    const selected = this.activeStage() === stage;
    if (selected) {
      return 'border-yellow-500 bg-yellow-100 text-dark-text shadow-sm';
    }
    return 'border-dark-border bg-white text-dark-muted hover:border-yellow-400 hover:bg-yellow-50 hover:text-dark-text';
  }

  toggleStage(stage: LifecycleStage | null): void {
    this.activeStage.set(this.activeStage() === stage ? null : stage);
  }

  private render(clusters: TrendmapCluster[]): void {
    const svg = d3.select(this.chartRef().nativeElement);
    svg.selectAll('*').remove();

    if (clusters.length === 0) {
      return;
    }

    const selectedStage = this.activeStage();
    const visibleClusters = selectedStage
      ? clusters.filter((cluster) => cluster.hype_stage === selectedStage)
      : clusters;
    svg
      .append('rect')
      .attr('width', WIDTH)
      .attr('height', HEIGHT)
      .attr('fill', DARK_THEME.bg)
      .attr('rx', 12);

    const innerWidth = WIDTH - MARGIN.left - MARGIN.right;
    const innerHeight = HEIGHT - MARGIN.top - MARGIN.bottom;
    const x = d3.scaleLinear().domain([0, 1]).range([MARGIN.left, MARGIN.left + innerWidth]);
    const y = d3.scaleLinear().domain([0, 1]).range([MARGIN.top + innerHeight, MARGIN.top]);

    const anchors: [number, number][] = STAGE_ORDER.map((stage) => [
      x(STAGE_X[stage]),
      y(STAGE_Y[stage]),
    ]);

    const curve = d3
      .line<[number, number]>()
      .x((point) => point[0])
      .y((point) => point[1])
      .curve(d3.curveBasis);

    const stageClusters = new Map<LifecycleStage, TrendmapCluster[]>();
    STAGE_ORDER.forEach((stage) => {
      stageClusters.set(
        stage,
        clusters.filter((cluster) => cluster.hype_stage === stage),
      );
    });

    const stageBandBoundaries = STAGE_ORDER.map((stage, index) => {
      const center = x(STAGE_X[stage]);
      const previous = index === 0 ? MARGIN.left : x(STAGE_X[STAGE_ORDER[index - 1]]);
      const next =
        index === STAGE_ORDER.length - 1
          ? WIDTH - MARGIN.right
          : x(STAGE_X[STAGE_ORDER[index + 1]]);
      const start = index === 0 ? MARGIN.left : (previous + center) / 2;
      const end = index === STAGE_ORDER.length - 1 ? WIDTH - MARGIN.right : (center + next) / 2;
      return { stage, start, end };
    });

    const stageLayer = svg.append('g');
    stageLayer
      .selectAll('rect.stage-band')
      .data(stageBandBoundaries)
      .join('rect')
      .attr('class', 'stage-band')
      .attr('x', (d) => d.start)
      .attr('y', MARGIN.top)
      .attr('width', (d) => d.end - d.start)
      .attr('height', innerHeight)
      .attr('fill', (d) => (selectedStage === d.stage ? 'rgba(245, 158, 11, 0.10)' : 'transparent'))
      .attr('stroke', 'transparent')
      .style('cursor', 'pointer')
      .on('mouseenter', (_event, d) => {
        this.showStageTooltip(d.stage, stageClusters.get(d.stage) ?? []);
      })
      .on('mousemove', (event) => {
        this.positionTooltip(event);
      })
      .on('mouseleave', () => {
        this.hideTooltip();
      })
      .on('click', (_event, d) => {
        this.toggleStage(d.stage);
      });

    svg
      .append('path')
      .datum([[x(0), y(0.16)], ...anchors, [x(1), y(0.7)]] as [number, number][])
      .attr('d', curve)
      .attr('fill', 'none')
      .attr('stroke', '#cbd5e1')
      .attr('stroke-width', 2.5)
      .attr('stroke-dasharray', '7,4');

    STAGE_ORDER.forEach((stage) => {
      const stageX = x(STAGE_X[stage]);
      svg
        .append('line')
        .attr('x1', stageX)
        .attr('x2', stageX)
        .attr('y1', MARGIN.top)
        .attr('y2', HEIGHT - MARGIN.bottom)
        .attr('stroke', DARK_THEME.border)
        .attr('stroke-dasharray', '3,6')
        .attr('stroke-opacity', 0.7);

      svg
        .append('text')
        .attr('x', stageX)
        .attr('y', HEIGHT - MARGIN.bottom + 18)
        .attr('text-anchor', 'middle')
        .attr('fill', DARK_THEME.textMuted)
        .attr('font-size', '9px')
        .text(STAGE_LABELS[stage]);
    });

    svg
      .append('text')
      .attr('x', 14)
      .attr('y', HEIGHT / 2)
      .attr('transform', `rotate(-90 14 ${HEIGHT / 2})`)
      .attr('fill', DARK_THEME.textMuted)
      .attr('font-size', '10px')
      .text('Visibilidad / expectativas');

    const radius = d3
      .scaleSqrt()
      .domain([0, d3.max(visibleClusters, (cluster) => cluster.item_count) ?? 1])
      .range([7, 26]);

    const orderedCategories = [...new Set(visibleClusters.map((cluster) => cluster.category))];
    const color = d3.scaleOrdinal<string, string>(d3.schemeTableau10).domain(orderedCategories);
    const stageBoundaryMap = new Map(stageBandBoundaries.map((band) => [band.stage, band]));
    const placedPoints: HypePoint[] = visibleClusters.map((cluster) => {
      const stage = cluster.hype_stage;
      const point: HypePoint = {
        cluster,
        stage,
        baseX: x(STAGE_X[stage]),
        baseY: y(STAGE_Y[stage]) - cluster.momentum_score * 0.12,
        x: x(STAGE_X[stage]),
        y: y(STAGE_Y[stage]) - cluster.momentum_score * 0.12,
        radius: radius(cluster.item_count),
        labelLines: this.wrapLabel(cluster.label, 18, 2),
        showLabel: false,
      };
      return point;
    });

    const simulation = d3
      .forceSimulation(placedPoints)
      .force('x', d3.forceX<HypePoint>((point) => point.baseX).strength(0.28))
      .force('y', d3.forceY<HypePoint>((point) => point.baseY).strength(0.22))
      .force('collide', d3.forceCollide<HypePoint>((point) => point.radius + 4).iterations(3))
      .stop();

    for (let tick = 0; tick < 220; tick += 1) {
      simulation.tick();
      placedPoints.forEach((point) => {
        const bounds = stageBoundaryMap.get(point.stage);
        if (!bounds) {
          return;
        }
        point.x = Math.max(bounds.start + point.radius + 6, Math.min(bounds.end - point.radius - 6, point.x));
        point.y = Math.max(MARGIN.top + point.radius + 6, Math.min(HEIGHT - MARGIN.bottom - point.radius - 14, point.y));
      });
    }

    const occupiedLabelRects: Array<{ left: number; right: number; top: number; bottom: number }> = [];
    [...placedPoints]
      .sort((a, b) => b.radius - a.radius || b.cluster.impact_score - a.cluster.impact_score)
      .forEach((point) => {
        if (point.radius < 10) {
          return;
        }
        const maxLineLength = Math.max(...point.labelLines.map((line) => line.length), 0);
        const labelWidth = maxLineLength * 6.2 + 14;
        const labelHeight = point.labelLines.length * 12 + 8;
        const left = point.x - labelWidth / 2;
        const right = point.x + labelWidth / 2;
        const bottom = point.y - point.radius - 8;
        const top = bottom - labelHeight;
        const insideChart = left >= MARGIN.left && right <= WIDTH - MARGIN.right && top >= MARGIN.top;
        const overlaps = occupiedLabelRects.some((rect) => !(right < rect.left || left > rect.right || bottom < rect.top || top > rect.bottom));
        if (insideChart && !overlaps) {
          point.showLabel = true;
          occupiedLabelRects.push({ left, right, top, bottom });
        }
      });

    placedPoints.forEach((point) => {
      const cluster = point.cluster;
      const stage = point.stage;

      const group = svg.append('g').style('cursor', 'pointer');
      group
        .append('circle')
        .attr('cx', point.x)
        .attr('cy', point.y)
        .attr('r', point.radius)
        .attr('fill', color(cluster.category))
        .attr('fill-opacity', 0.9)
        .attr('stroke', selectedStage === stage ? '#2c2a29' : '#ffffff')
        .attr('stroke-opacity', selectedStage === stage ? 0.9 : 0.95)
        .attr('stroke-width', selectedStage === stage ? 2.0 : 1.2)
        .on('mouseenter', (event) => {
          this.showClusterGroupTooltip(this.overlappingPoints(point, placedPoints));
          this.positionTooltip(event);
        })
        .on('mousemove', (event) => {
          this.positionTooltip(event);
        })
        .on('mouseleave', () => {
          this.hideTooltip();
        })
        .on('click', () => {
          this.clusterSelected.emit(cluster);
        });

      if (point.showLabel) {
        group
          .append('line')
          .attr('x1', point.x)
          .attr('x2', point.x)
          .attr('y1', point.y - point.radius - 2)
          .attr('y2', point.y - point.radius - 12)
          .attr('stroke', color(cluster.category))
          .attr('stroke-opacity', 0.45)
          .attr('stroke-width', 1);

        const labelGroup = group
          .append('g')
          .attr('transform', `translate(${point.x}, ${point.y - point.radius - 16})`)
          .attr('pointer-events', 'none');

        const labelText = labelGroup
          .append('text')
          .attr('text-anchor', 'middle')
          .attr('fill', DARK_THEME.text)
          .attr('font-size', '9.5px')
          .attr('font-weight', '600');

        point.labelLines.forEach((line, index) => {
          labelText
            .append('tspan')
            .attr('x', 0)
            .attr('dy', index === 0 ? `${-(point.labelLines.length - 1) * 0.55}em` : '1.1em')
            .text(line);
        });

        const bounds = (labelText.node() as SVGTextElement).getBBox();
        labelGroup
          .insert('rect', 'text')
          .attr('x', bounds.x - 6)
          .attr('y', bounds.y - 3)
          .attr('width', bounds.width + 12)
          .attr('height', bounds.height + 6)
          .attr('rx', 6)
          .attr('fill', 'rgba(255, 255, 255, 0.94)')
          .attr('stroke', '#e2e8f0')
          .attr('stroke-opacity', 0.9)
          .attr('stroke-width', 0.9);
      }
    });
  }

  private ensureTooltip(): HTMLDivElement {
    if (this.tooltip) {
      return this.tooltip;
    }
    const tooltip = document.createElement('div');
    tooltip.className = 'trendmap-hype-tooltip';
    tooltip.style.position = 'fixed';
    tooltip.style.pointerEvents = 'none';
    tooltip.style.zIndex = '1000';
    tooltip.style.maxWidth = '320px';
    tooltip.style.padding = '10px 12px';
    tooltip.style.borderRadius = '14px';
    tooltip.style.border = '1px solid rgba(226, 232, 240, 0.95)';
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

  private showClusterGroupTooltip(points: HypePoint[]): void {
    const tooltip = this.ensureTooltip();
    const clusters = points.map((point) => point.cluster);
    const primary = clusters[0];
    if (!primary) {
      return;
    }
    if (clusters.length > 1) {
      const rows = clusters
        .slice(0, 6)
        .map((cluster) => `
          <div style="border-top:1px solid #e2e8f0; margin-top:8px; padding-top:8px;">
            <div style="font-weight:700; color:#2c2a29;">${this.escapeHtml(cluster.label)}</div>
            <div style="color:#64748b;">${this.escapeHtml(cluster.category)} | ${this.escapeHtml(this.stageLabel(cluster.hype_stage))}</div>
            <div style="margin-top:4px;">Impacto ${cluster.impact_score.toFixed(0)} | Madurez ${cluster.maturity_score.toFixed(0)} | Dinamica ${cluster.momentum_score.toFixed(0)}</div>
            <div style="margin-top:4px; color:#475569;">${this.escapeHtml(cluster.executive_takeaway || cluster.summary)}</div>
          </div>
        `)
        .join('');
      tooltip.innerHTML = `
        <div style="font-weight:700; color:#2c2a29;">${clusters.length} elementos superpuestos o cercanos</div>
        <div style="margin-top:2px; color:#64748b;">Click en una burbuja para seleccionar el cluster visible.</div>
        ${rows}
      `;
      tooltip.style.opacity = '1';
      return;
    }

    const keywords = primary.top_keywords.slice(0, 3).join(', ');
    tooltip.innerHTML = `
      <div style="font-weight:700; color:#2c2a29;">${this.escapeHtml(primary.label)}</div>
      <div style="margin-top:2px; color:#64748b;">${this.escapeHtml(primary.category)} | ${this.escapeHtml(this.stageLabel(primary.hype_stage))}</div>
      <div style="margin-top:8px;">
        Impacto ${primary.impact_score.toFixed(0)} | Madurez ${primary.maturity_score.toFixed(0)} | Dinamica ${primary.momentum_score.toFixed(0)}
      </div>
      <div>Documentos ${primary.item_count} | Calidad ${primary.cluster_quality.score.toFixed(0)}</div>
      <div style="margin-top:8px; color:#475569;">${this.escapeHtml(primary.executive_takeaway || primary.summary)}</div>
      <div style="margin-top:8px; color:#64748b;">${this.escapeHtml(keywords)}</div>
    `;
    tooltip.style.opacity = '1';
  }

  private showStageTooltip(stage: LifecycleStage, clusters: TrendmapCluster[]): void {
    const tooltip = this.ensureTooltip();
    const labels = clusters
      .slice(0, 6)
      .map((cluster) => this.escapeHtml(cluster.label))
      .join('<br/>');
    tooltip.innerHTML = `
      <div style="font-weight:700; color:#2c2a29;">${this.escapeHtml(this.stageLabel(stage))}</div>
      <div style="margin-top:2px; color:#64748b;">${clusters.length} clusters en esta etapa</div>
      <div style="margin-top:8px; color:#475569;">${labels || 'Sin clusters visibles'}</div>
      <div style="margin-top:8px; color:#64748b;">Click para filtrar esta etapa</div>
    `;
    tooltip.style.opacity = '1';
  }

  private positionTooltip(event: MouseEvent): void {
    const tooltip = this.ensureTooltip();
    tooltip.style.left = `${event.clientX + 14}px`;
    tooltip.style.top = `${event.clientY + 14}px`;
  }

  private hideTooltip(): void {
    if (this.tooltip) {
      this.tooltip.style.opacity = '0';
    }
  }

  private overlappingPoints(target: HypePoint, points: HypePoint[]): HypePoint[] {
    return points.filter((point) => {
      const dx = point.x - target.x;
      const dy = point.y - target.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      return point.stage === target.stage
        && distance <= Math.max(34, point.radius + target.radius + 6);
    });
  }

  private wrapLabel(label: string, maxCharsPerLine: number, maxLines: number): string[] {
    const words = label.split(/\s+/);
    const lines: string[] = [];
    let currentLine = '';

    words.forEach((word) => {
      const candidate = currentLine ? `${currentLine} ${word}` : word;
      if (candidate.length <= maxCharsPerLine) {
        currentLine = candidate;
        return;
      }

      if (currentLine) {
        lines.push(currentLine);
      }
      currentLine = word.length > maxCharsPerLine ? `${word.slice(0, maxCharsPerLine - 1)}…` : word;
    });

    if (currentLine) {
      lines.push(currentLine);
    }

    const limited = lines.slice(0, maxLines);
    if (lines.length > maxLines) {
      const last = limited[maxLines - 1];
      limited[maxLines - 1] = last.endsWith('…') ? last : `${last.slice(0, Math.max(0, maxCharsPerLine - 1))}…`;
    }
    return limited;
  }

  private escapeHtml(value: string): string {
    return value
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }
}
