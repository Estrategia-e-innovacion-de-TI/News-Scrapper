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
  RiskmapCluster,
  TrendmapArticle,
} from '../../../../../domain/noticias/models';

const WIDTH = 800;
const HEIGHT = 550;
const MARGIN = { top: 20, right: 20, bottom: 30, left: 40 };

type TooltipSelection = d3.Selection<HTMLDivElement, null, d3.BaseType, unknown>;

const SOURCE_TYPE_LABELS: Record<string, string> = {
  news: 'Noticias',
  rss: 'Articulos y blogs',
  paper: 'Articulos academicos',
  pdf: 'Documentos tecnicos',
  patent: 'Patentes',
  institutional_report: 'Reportes institucionales',
};

@Component({
  selector: 'app-riskmap-d3-scatter',
  standalone: true,
  template: `
    <div class="rounded-2xl border border-dark-border bg-dark-surface p-4">
      <h4 class="mb-1 text-sm font-semibold text-dark-text">Mapa de articulos (UMAP)</h4>
      <p class="mb-3 text-xs leading-5 text-dark-muted">
        Proyeccion semantica de documentos de riesgo. Color por categoria. Pasa el cursor sobre grupos o articulos para ver detalles.
      </p>
      <svg #chart [attr.width]="width" [attr.height]="height"></svg>
    </div>
  `,
})
export class RiskmapD3ScatterComponent implements AfterViewInit {
  readonly articles = input<TrendmapArticle[]>([]);
  readonly clusters = input<RiskmapCluster[]>([]);
  readonly selectedCluster = input<RiskmapCluster | null>(null);
  readonly clusterSelected = output<RiskmapCluster | null>();
  readonly chartRef = viewChild.required<ElementRef<SVGSVGElement>>('chart');

  readonly width = WIDTH;
  readonly height = HEIGHT;

  private initialized = false;

  constructor() {
    effect(() => {
      const arts = this.articles();
      const cls = this.clusters();
      const sel = this.selectedCluster();
      if (this.initialized) {
        this.render(arts, cls, sel);
      }
    });
  }

  ngAfterViewInit(): void {
    this.initialized = true;
    this.render(this.articles(), this.clusters(), this.selectedCluster());
  }

  private render(
    articles: TrendmapArticle[],
    clusters: RiskmapCluster[],
    selectedCluster: RiskmapCluster | null,
  ): void {
    const svg = d3.select(this.chartRef().nativeElement);
    svg.selectAll('*').remove();

    if (articles.length === 0) return;

    svg
      .append('rect')
      .attr('width', WIDTH)
      .attr('height', HEIGHT)
      .attr('fill', DARK_THEME.bg)
      .attr('rx', 8);

    const g = svg.append('g');

    const xExtent = d3.extent(articles, (d) => d.x_embed) as [number, number];
    const yExtent = d3.extent(articles, (d) => d.y_embed) as [number, number];
    const xPad = (xExtent[1] - xExtent[0]) * 0.05 || 1;
    const yPad = (yExtent[1] - yExtent[0]) * 0.05 || 1;

    const x = d3
      .scaleLinear()
      .domain([xExtent[0] - xPad, xExtent[1] + xPad])
      .range([MARGIN.left, WIDTH - MARGIN.right]);

    const y = d3
      .scaleLinear()
      .domain([yExtent[0] - yPad, yExtent[1] + yPad])
      .range([HEIGHT - MARGIN.bottom, MARGIN.top]);

    const orderedCategories = [...new Set(clusters.map((c) => c.category))];
    const color = d3.scaleOrdinal<string, string>(d3.schemeTableau10).domain(orderedCategories);

    const tooltip: TooltipSelection = d3
      .select('body')
      .selectAll<HTMLDivElement, null>('div.riskmap-record-tooltip')
      .data([null])
      .join('div')
      .attr('class', 'riskmap-record-tooltip')
      .style('position', 'absolute')
      .style('max-width', '360px')
      .style('background', DARK_THEME.surface)
      .style('border', `1px solid ${DARK_THEME.border}`)
      .style('color', DARK_THEME.text)
      .style('padding', '10px 12px')
      .style('border-radius', '10px')
      .style('font-size', '12px')
      .style('line-height', '1.45')
      .style('box-shadow', '0 12px 30px rgba(15, 23, 42, 0.35)')
      .style('pointer-events', 'none')
      .style('opacity', 0)
      .style('z-index', '1200');

    const clusterMap = new Map(clusters.map((c) => [c.cluster_id, c]));

    // Hull polygons
    clusters.forEach((cluster) => {
      if ((cluster.hull_polygon?.length ?? 0) < 3) return;
      const polygon = (cluster.hull_polygon ?? []).map(([px, py]) => [x(px), y(py)] as [number, number]);
      const isSelected = selectedCluster?.cluster_id === cluster.cluster_id;

      g.append('path')
        .datum(polygon)
        .attr('d', (d) => `M${d.join('L')}Z`)
        .attr('fill', color(cluster.category))
        .attr('fill-opacity', isSelected ? 0.25 : 0.08)
        .attr('stroke', color(cluster.category))
        .attr('stroke-opacity', isSelected ? 0.8 : 0.3)
        .attr('stroke-width', isSelected ? 2 : 1)
        .attr('cursor', 'pointer')
        .on('mouseenter', (event: MouseEvent) => {
          this.showClusterTooltip(tooltip, event, cluster);
        })
        .on('mousemove', (event: MouseEvent) => {
          this.positionTooltip(tooltip, event);
        })
        .on('mouseleave', () => tooltip.style('opacity', 0))
        .on('click', () => {
          this.clusterSelected.emit(
            selectedCluster?.cluster_id === cluster.cluster_id ? null : cluster,
          );
        });
    });

    // Article dots
    g.selectAll('circle.article')
      .data(articles)
      .join('circle')
      .attr('class', 'article')
      .attr('cx', (d) => x(d.x_embed))
      .attr('cy', (d) => y(d.y_embed))
      .attr('r', (d) => {
        if (selectedCluster && d.cluster_id === selectedCluster.cluster_id) return 5;
        if (selectedCluster) return 2;
        return 3.5;
      })
      .attr('fill', (d) => {
        const cluster = clusterMap.get(d.cluster_id);
        return color(cluster?.category ?? 'unknown');
      })
      .attr('opacity', (d) => {
        if (selectedCluster && d.cluster_id !== selectedCluster.cluster_id) return 0.2;
        return 0.8;
      })
      .attr('stroke', DARK_THEME.bg)
      .attr('stroke-width', 0.5)
      .attr('cursor', 'pointer')
      .on('mouseenter', (event: MouseEvent, d: TrendmapArticle) => {
        const safeTitle = this.escapeHtml(d.title);
        const safeUrl = this.escapeHtml(d.url || 'sin URL');
        const safeCluster = this.escapeHtml(d.cluster_label || clusterMap.get(d.cluster_id)?.label || d.cluster_id);
        const safeSource = this.escapeHtml(d.source || 'fuente');
        const riskCluster = clusterMap.get(d.cluster_id);
        tooltip
          .style('opacity', 1)
          .html(
            `<div style="font-weight:600; margin-bottom:6px;">${safeTitle}</div>` +
              `<div style="margin-bottom:6px; color:${DARK_THEME.textMuted};">${safeCluster} | ${safeSource}</div>` +
              `<div style="margin-bottom:6px; color:${DARK_THEME.textMuted};">Puntaje ${d.score.toFixed(0)} | ${this.escapeHtml(SOURCE_TYPE_LABELS[d.source_type] ?? d.source_type)}</div>` +
              (riskCluster ? `<div style="color:${DARK_THEME.textMuted};">Severidad ${riskCluster.risk_severity.toFixed(0)} | Persistencia ${riskCluster.persistence_score.toFixed(0)}</div>` : '') +
              `<div style="margin-top:4px; color:${DARK_THEME.textMuted}; word-break:break-word;">${safeUrl}</div>`,
          );
        this.positionTooltip(tooltip, event);
      })
      .on('mousemove', (event: MouseEvent) => {
        this.positionTooltip(tooltip, event);
      })
      .on('mouseleave', () => tooltip.style('opacity', 0))
      .on('click', (_event: MouseEvent, d: TrendmapArticle) => {
        const cluster = clusterMap.get(d.cluster_id) ?? null;
        this.clusterSelected.emit(
          selectedCluster?.cluster_id === d.cluster_id ? null : cluster,
        );
      });

    // Cluster labels at centroids
    const articlesByCluster = d3.group(articles, (a) => a.cluster_id);
    articlesByCluster.forEach((clusterArticles, clusterId) => {
      const cluster = clusterMap.get(clusterId);
      if (!cluster) return;

      const cx = d3.mean(clusterArticles, (a) => x(a.x_embed)) ?? 0;
      const cy = d3.mean(clusterArticles, (a) => y(a.y_embed)) ?? 0;
      const labelLines = this.wrapClusterLabel(cluster.label, 18);
      const labelGroup = g
        .append('g')
        .attr('transform', `translate(${cx}, ${cy})`)
        .attr('cursor', 'pointer')
        .on('mouseenter', (event: MouseEvent) => {
          this.showClusterTooltip(tooltip, event, cluster);
        })
        .on('mousemove', (event: MouseEvent) => {
          this.positionTooltip(tooltip, event);
        })
        .on('mouseleave', () => tooltip.style('opacity', 0))
        .on('click', () => {
          this.clusterSelected.emit(
            selectedCluster?.cluster_id === cluster.cluster_id ? null : cluster,
          );
        });

      const labelText = labelGroup
        .append('text')
        .attr('text-anchor', 'middle')
        .attr('font-size', '10.5px')
        .attr('font-weight', '700')
        .attr('fill', color(cluster.category));

      labelLines.forEach((line, index) => {
        labelText
          .append('tspan')
          .attr('x', 0)
          .attr('dy', index === 0 ? `${-(labelLines.length - 1) * 0.6}em` : '1.15em')
          .text(line);
      });

      const textBounds = (labelText.node() as SVGTextElement).getBBox();
      labelGroup
        .insert('rect', 'text')
        .attr('x', textBounds.x - 6)
        .attr('y', textBounds.y - 3)
        .attr('width', textBounds.width + 12)
        .attr('height', textBounds.height + 6)
        .attr('rx', 6)
        .attr('fill', 'rgba(248, 250, 252, 0.92)')
        .attr('stroke', color(cluster.category))
        .attr('stroke-opacity', 0.2)
        .attr('stroke-width', 0.8);
    });

    // Zoom/pan
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 8])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoom);
  }

  private showClusterTooltip(
    tooltip: TooltipSelection,
    event: MouseEvent,
    cluster: RiskmapCluster,
  ): void {
    const safeLabel = this.escapeHtml(cluster.label);
    const safeCategory = this.escapeHtml(cluster.dominant_risk || cluster.category);
    const safeSummary = this.escapeHtml(cluster.executive_takeaway || cluster.summary);
    tooltip
      .style('opacity', 1)
      .html(
        `<div style="font-weight:700; margin-bottom:6px;">${safeLabel}</div>` +
          `<div style="margin-bottom:6px; color:${DARK_THEME.textMuted};">${safeCategory} | Documentos ${cluster.item_count}</div>` +
          `<div style="margin-bottom:6px; color:${DARK_THEME.textMuted};">Severidad ${cluster.risk_severity.toFixed(0)} | Persistencia ${cluster.persistence_score.toFixed(0)} | Dinamica ${cluster.momentum_score.toFixed(0)}</div>` +
          `<div style="color:${DARK_THEME.textMuted};">${safeSummary}</div>`,
      );
    this.positionTooltip(tooltip, event);
  }

  private positionTooltip(tooltip: TooltipSelection, event: MouseEvent): void {
    tooltip
      .style('left', `${event.pageX + 14}px`)
      .style('top', `${event.pageY - 12}px`);
  }

  private escapeHtml(value: string): string {
    return value
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  private wrapClusterLabel(label: string, maxCharsPerLine: number): string[] {
    const words = label.split(/\s+/).flatMap((word) => this.splitLongWord(word, maxCharsPerLine));
    const lines: string[] = [];
    let currentLine = '';
    words.forEach((word) => {
      const candidate = currentLine ? `${currentLine} ${word}` : word;
      if (candidate.length <= maxCharsPerLine) {
        currentLine = candidate;
        return;
      }
      if (currentLine) lines.push(currentLine);
      currentLine = word;
    });
    if (currentLine) lines.push(currentLine);
    return lines.slice(0, 4);
  }

  private splitLongWord(word: string, maxCharsPerLine: number): string[] {
    if (word.length <= maxCharsPerLine) return [word];
    const chunks: string[] = [];
    for (let i = 0; i < word.length; i += maxCharsPerLine) {
      chunks.push(word.slice(i, i + maxCharsPerLine));
    }
    return chunks;
  }
}
