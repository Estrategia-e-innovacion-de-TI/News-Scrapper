import {
  Component,
  ElementRef,
  input,
  output,
  effect,
  viewChild,
  AfterViewInit,
} from '@angular/core';
import {
  TrendmapArticle,
  TrendmapCluster,
  DARK_THEME,
} from '../../../../../domain/noticias/models';
import * as d3 from 'd3';

const WIDTH = 800;
const HEIGHT = 550;
const MARGIN = { top: 20, right: 20, bottom: 30, left: 40 };

@Component({
  selector: 'app-d3-scatter',
  standalone: true,
  template: `
    <div class="bg-dark-surface border border-dark-border rounded-lg p-4">
      <h4 class="text-sm font-semibold text-dark-text mb-2">Mapa de Artículos (UMAP)</h4>
      <svg #chart [attr.width]="width" [attr.height]="height"></svg>
    </div>
  `,
})
export class D3ScatterComponent implements AfterViewInit {
  readonly articles = input<TrendmapArticle[]>([]);
  readonly clusters = input<TrendmapCluster[]>([]);
  readonly selectedCluster = input<TrendmapCluster | null>(null);
  readonly clusterSelected = output<TrendmapCluster | null>();
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
    clusters: TrendmapCluster[],
    selectedCluster: TrendmapCluster | null,
  ): void {
    const svg = d3.select(this.chartRef().nativeElement);
    svg.selectAll('*').remove();

    if (articles.length === 0) return;

    // Background
    svg
      .append('rect')
      .attr('width', WIDTH)
      .attr('height', HEIGHT)
      .attr('fill', DARK_THEME.bg)
      .attr('rx', 8);

    const g = svg.append('g');

    // Scales
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

    const color = d3.scaleOrdinal(d3.schemeTableau10);

    // Build cluster map for quick lookup
    const clusterMap = new Map(clusters.map((c) => [c.cluster_id, c]));

    // Draw hull polygons per cluster
    const articlesByCluster = d3.group(articles, (a) => a.cluster_id);

    articlesByCluster.forEach((clusterArticles, clusterId) => {
      if (clusterArticles.length < 3) return;

      const points: [number, number][] = clusterArticles.map((a) => [
        x(a.x_embed),
        y(a.y_embed),
      ]);

      const hull = d3.polygonHull(points);
      if (!hull) return;

      const cluster = clusterMap.get(clusterId);
      const cat = cluster?.category ?? 'unknown';
      const isSelected = selectedCluster?.cluster_id === clusterId;

      g.append('path')
        .datum(hull)
        .attr('d', (d) => `M${d.join('L')}Z`)
        .attr('fill', color(cat))
        .attr('fill-opacity', isSelected ? 0.25 : 0.08)
        .attr('stroke', color(cat))
        .attr('stroke-opacity', isSelected ? 0.8 : 0.3)
        .attr('stroke-width', isSelected ? 2 : 1)
        .attr('cursor', 'pointer')
        .on('click', () => {
          this.clusterSelected.emit(
            selectedCluster?.cluster_id === clusterId ? null : (cluster ?? null),
          );
        });
    });

    // Draw article points
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
      .on('click', (_event: MouseEvent, d: TrendmapArticle) => {
        const cluster = clusterMap.get(d.cluster_id) ?? null;
        this.clusterSelected.emit(
          selectedCluster?.cluster_id === d.cluster_id ? null : cluster,
        );
      });

    // Cluster labels at centroids
    articlesByCluster.forEach((clusterArticles, clusterId) => {
      const cluster = clusterMap.get(clusterId);
      if (!cluster) return;

      const cx = d3.mean(clusterArticles, (a) => x(a.x_embed)) ?? 0;
      const cy = d3.mean(clusterArticles, (a) => y(a.y_embed)) ?? 0;

      g.append('text')
        .attr('x', cx)
        .attr('y', cy)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'central')
        .attr('font-size', '10px')
        .attr('font-weight', '600')
        .attr('fill', color(cluster.category))
        .attr('pointer-events', 'none')
        .text(cluster.label.length > 20 ? cluster.label.slice(0, 20) + '…' : cluster.label);
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
}
