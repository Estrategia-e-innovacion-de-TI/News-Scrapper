import {
  AfterViewInit,
  Component,
  ElementRef,
  effect,
  input,
  output,
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
  weak_signal: 'Weak Signal',
  innovation_trigger: 'Innovation Trigger',
  rising_attention: 'Rising Attention',
  peak_visibility: 'Peak Visibility',
  correction: 'Correction',
  consolidation: 'Consolidation',
  productive_adoption: 'Productive Adoption',
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

@Component({
  selector: 'app-hype-cycle',
  standalone: true,
  template: `
    <div class="rounded-2xl border border-dark-border bg-dark-surface p-4">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h4 class="text-sm font-semibold text-dark-text">Hype cycle operativo</h4>
          <p class="mt-1 text-xs leading-5 text-dark-muted">
            La etapa sale de madurez, impacto, momentum, novedad e incertidumbre. Haz hover
            sobre una etapa o burbuja para ver el detalle.
          </p>
        </div>
        <button
          class="rounded-full border border-dark-border bg-dark-bg px-3 py-1 text-xs text-dark-muted transition hover:text-dark-text"
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
            <span class="ml-2 rounded-full bg-dark-bg px-2 py-0.5 text-[10px] text-dark-muted">
              {{ stageCount(stage) }}
            </span>
          </button>
        }
      </div>

      <svg #chart class="mt-4" [attr.width]="width" [attr.height]="height"></svg>
    </div>
  `,
})
export class HypeCycleComponent implements AfterViewInit {
  readonly clusters = input<TrendmapCluster[]>([]);
  readonly selectedStage = input<LifecycleStage | null>(null);
  readonly chartRef = viewChild.required<ElementRef<SVGSVGElement>>('chart');

  readonly stageSelected = output<LifecycleStage | null>();
  readonly clusterSelected = output<TrendmapCluster | null>();

  readonly width = WIDTH;
  readonly height = HEIGHT;
  readonly stageOrder = STAGE_ORDER;

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

  stageLabel(stage: LifecycleStage): string {
    return STAGE_LABELS[stage];
  }

  stageCount(stage: LifecycleStage): number {
    return this.clusters().filter((cluster) => cluster.hype_stage === stage).length;
  }

  stageChipClass(stage: LifecycleStage): string {
    const selected = this.selectedStage() === stage;
    if (selected) {
      return 'border-amber-500/50 bg-amber-500/10 text-amber-200';
    }
    return 'border-dark-border bg-dark-bg text-dark-muted hover:border-dark-muted hover:text-dark-text';
  }

  toggleStage(stage: LifecycleStage | null): void {
    this.stageSelected.emit(this.selectedStage() === stage ? null : stage);
  }

  private render(clusters: TrendmapCluster[]): void {
    const svg = d3.select(this.chartRef().nativeElement);
    svg.selectAll('*').remove();

    if (clusters.length === 0) {
      return;
    }

    const selectedStage = this.selectedStage();
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
      .attr('stroke', '#475569')
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
      .domain([0, d3.max(clusters, (cluster) => cluster.item_count) ?? 1])
      .range([7, 26]);

    const color = d3.scaleOrdinal<string, string>(d3.schemeTableau10);
    const stageCounts = new Map<LifecycleStage, number>();

    clusters.forEach((cluster) => {
      const stage = cluster.hype_stage;
      const currentCount = stageCounts.get(stage) ?? 0;
      stageCounts.set(stage, currentCount + 1);

      const baseX = x(STAGE_X[stage]);
      const baseY = y(STAGE_Y[stage]);
      const jitterX = ((currentCount % 4) - 1.5) * 18;
      const jitterY = Math.floor(currentCount / 4) * 16 - cluster.momentum_score * 0.15;
      const bubbleX = baseX + jitterX;
      const bubbleY = baseY + jitterY;
      const bubbleRadius = radius(cluster.item_count);

      const group = svg.append('g').style('cursor', 'pointer');
      group
        .append('circle')
        .attr('cx', bubbleX)
        .attr('cy', bubbleY)
        .attr('r', bubbleRadius)
        .attr('fill', color(cluster.category))
        .attr('fill-opacity', 0.82)
        .attr('stroke', selectedStage === stage ? '#fbbf24' : '#e2e8f0')
        .attr('stroke-opacity', selectedStage === stage ? 0.9 : 0.15)
        .attr('stroke-width', selectedStage === stage ? 2.0 : 1.2)
        .on('mouseenter', (event) => {
          this.showClusterTooltip(cluster);
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

      if (bubbleRadius >= 12) {
        group
          .append('text')
          .attr('x', bubbleX)
          .attr('y', bubbleY - bubbleRadius - 8)
          .attr('text-anchor', 'middle')
          .attr('fill', DARK_THEME.text)
          .attr('font-size', '8px')
          .text(cluster.label.length > 22 ? `${cluster.label.slice(0, 22)}...` : cluster.label);
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
    tooltip.style.border = '1px solid rgba(148, 163, 184, 0.28)';
    tooltip.style.background = 'rgba(15, 23, 42, 0.96)';
    tooltip.style.color = '#dbe4f0';
    tooltip.style.boxShadow = '0 16px 30px rgba(2, 6, 23, 0.35)';
    tooltip.style.fontSize = '12px';
    tooltip.style.lineHeight = '1.5';
    tooltip.style.opacity = '0';
    tooltip.style.transition = 'opacity 120ms ease';
    document.body.appendChild(tooltip);
    this.tooltip = tooltip;
    return tooltip;
  }

  private showClusterTooltip(cluster: TrendmapCluster): void {
    const tooltip = this.ensureTooltip();
    const keywords = cluster.top_keywords.slice(0, 3).join(', ');
    tooltip.innerHTML = `
      <div style="font-weight:600; color:#f8fafc;">${this.escapeHtml(cluster.label)}</div>
      <div style="margin-top:2px; color:#94a3b8;">${this.escapeHtml(cluster.category)} | ${this.escapeHtml(this.stageLabel(cluster.hype_stage))}</div>
      <div style="margin-top:8px;">
        Impacto ${cluster.impact_score.toFixed(0)} | Madurez ${cluster.maturity_score.toFixed(0)} | Momentum ${cluster.momentum_score.toFixed(0)}
      </div>
      <div>Docs ${cluster.item_count} | Calidad ${cluster.cluster_quality.score.toFixed(0)}</div>
      <div style="margin-top:8px; color:#cbd5e1;">${this.escapeHtml(cluster.executive_takeaway)}</div>
      <div style="margin-top:8px; color:#94a3b8;">${this.escapeHtml(keywords)}</div>
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
      <div style="font-weight:600; color:#f8fafc;">${this.escapeHtml(this.stageLabel(stage))}</div>
      <div style="margin-top:2px; color:#94a3b8;">${clusters.length} clusters en esta etapa</div>
      <div style="margin-top:8px; color:#cbd5e1;">${labels || 'Sin clusters visibles'}</div>
      <div style="margin-top:8px; color:#94a3b8;">Click para filtrar esta etapa</div>
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

  private escapeHtml(value: string): string {
    return value
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }
}
