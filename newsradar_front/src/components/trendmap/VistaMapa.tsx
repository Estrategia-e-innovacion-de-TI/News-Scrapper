/**
 * VistaMapa — Scatter plot of article embeddings with cluster hulls and centroids.
 *
 * Uses scattergl for performance. Differentiates news (circle/6) from papers
 * (diamond/8), draws super-cluster hulls (dashed), sub-cluster hulls (dotted),
 * and centroid stars (size 16) with colored labels.
 *
 * Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
 */
import React, { useMemo } from "react";
import type { Data, Layout } from "plotly.js";
import PlotlyWrapper from "@/components/trendmap/PlotlyWrapper";
import { useTrendmap } from "@/components/trendmap/trendmapContext";
import { CAT_COLORS } from "@/lib/catColors";
import type { Article, Cluster, SuperCluster } from "@/lib/api";

// ── Helpers ──────────────────────────────────────────────────────────

function colorForCategory(cat: string | null): string {
  return CAT_COLORS[cat ?? "Otros"] ?? CAT_COLORS["Otros"];
}

/** Convert hex color to rgba with given alpha */
function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

// ── Trace builders (exported for testing) ────────────────────────────

/**
 * Build article scatter traces — one per source_type.
 * News: circle size 6, Papers: diamond size 8. Colors by article category.
 */
export function buildArticleTraces(articles: Article[]): Data[] {
  const news = articles.filter((a) => a.source_type === "news");
  const papers = articles.filter((a) => a.source_type === "paper");

  const traces: Data[] = [];

  if (news.length > 0) {
    traces.push({
      type: "scattergl",
      mode: "markers",
      name: "Noticias",
      x: news.map((a) => a.x_embed),
      y: news.map((a) => a.y_embed),
      marker: {
        symbol: "circle",
        size: 6,
        color: news.map((a) => colorForCategory(a.category)),
        opacity: 0.8,
      },
      text: news.map(
        (a) =>
          `<b>${a.title}</b><br>Score: ${a.relevance_score}<br>Fuente: ${a.source_id}`,
      ),
      hoverinfo: "text" as const,
      hovertemplate:
        "<b>%{customdata[0]}</b><br>Score: %{customdata[1]}<br>Fuente: %{customdata[2]}<extra></extra>",
      customdata: news.map((a) => [a.title, a.relevance_score, a.source_id]),
    } as Data);
  }

  if (papers.length > 0) {
    traces.push({
      type: "scattergl",
      mode: "markers",
      name: "Papers",
      x: papers.map((a) => a.x_embed),
      y: papers.map((a) => a.y_embed),
      marker: {
        symbol: "diamond",
        size: 8,
        color: papers.map((a) => colorForCategory(a.category)),
        opacity: 0.8,
      },
      hovertemplate:
        "<b>%{customdata[0]}</b><br>Score: %{customdata[1]}<br>Fuente: %{customdata[2]}<extra></extra>",
      customdata: papers.map((a) => [a.title, a.relevance_score, a.source_id]),
    } as Data);
  }

  return traces;
}


/**
 * Build hull traces for super-clusters (dashed lines, semi-transparent fill).
 */
export function buildSuperClusterHulls(superClusters: SuperCluster[]): Data[] {
  return superClusters
    .filter((sc) => sc.hull_polygon && sc.hull_polygon.length >= 3)
    .map((sc) => {
      const color = colorForCategory(sc.category);
      // Close the polygon by repeating the first point
      const xs = [...sc.hull_polygon.map((p) => p[0]), sc.hull_polygon[0][0]];
      const ys = [...sc.hull_polygon.map((p) => p[1]), sc.hull_polygon[0][1]];

      return {
        type: "scatter" as const,
        mode: "lines" as const,
        name: `Super: ${sc.category}`,
        x: xs,
        y: ys,
        line: { color, dash: "dash" as const, width: 2 },
        fill: "toself" as const,
        fillcolor: hexToRgba(color, 0.08),
        hoverinfo: "name" as const,
        showlegend: false,
      } as Data;
    });
}

/**
 * Build hull traces for sub-clusters (dotted lines, semi-transparent fill).
 */
export function buildClusterHulls(clusters: Cluster[]): Data[] {
  return clusters
    .filter((c) => c.hull_polygon && c.hull_polygon.length >= 3)
    .map((c) => {
      const color = colorForCategory(c.category);
      const xs = [...c.hull_polygon.map((p) => p[0]), c.hull_polygon[0][0]];
      const ys = [...c.hull_polygon.map((p) => p[1]), c.hull_polygon[0][1]];

      return {
        type: "scatter" as const,
        mode: "lines" as const,
        name: c.label,
        x: xs,
        y: ys,
        line: { color, dash: "dot" as const, width: 1.5 },
        fill: "toself" as const,
        fillcolor: hexToRgba(color, 0.05),
        hoverinfo: "name" as const,
        showlegend: false,
      } as Data;
    });
}

/**
 * Build centroid trace — stars (size 16) with colored labels.
 */
export function buildCentroidTrace(clusters: Cluster[]): Data | null {
  const valid = clusters.filter(
    (c) => c.x_embed != null && c.y_embed != null,
  );
  if (valid.length === 0) return null;

  return {
    type: "scatter" as const,
    mode: "markers+text" as const,
    name: "Centroides",
    x: valid.map((c) => c.x_embed),
    y: valid.map((c) => c.y_embed),
    marker: {
      symbol: "star",
      size: 16,
      color: valid.map((c) => colorForCategory(c.category)),
      line: { color: "#fff", width: 1 },
    },
    text: valid.map((c) => c.label),
    textposition: "top center" as const,
    textfont: {
      size: 10,
      color: valid.map((c) => colorForCategory(c.category)),
    },
    hovertemplate:
      "<b>%{text}</b><br>Categoría: %{customdata}<extra></extra>",
    customdata: valid.map((c) => c.category),
    showlegend: false,
  } as Data;
}

// ── Layout builder ───────────────────────────────────────────────────

export function buildMapLayout(): Partial<Layout> {
  return {
    title: { text: "Mapa de Embeddings", font: { size: 16 } },
    xaxis: {
      title: "Dimensión 1",
      zeroline: false,
      showgrid: false,
    },
    yaxis: {
      title: "Dimensión 2",
      zeroline: false,
      showgrid: false,
    },
    hovermode: "closest" as const,
    showlegend: true,
    legend: { x: 0, y: -0.15, orientation: "h" as const },
    margin: { t: 40, r: 20, b: 60, l: 50 },
    paper_bgcolor: "transparent",
    plot_bgcolor: "#fafafa",
  };
}

// ── Component ────────────────────────────────────────────────────────

export default function VistaMapa() {
  const { filteredArticles, filteredClusters, superClusters } = useTrendmap();

  const { data, layout } = useMemo(() => {
    const traces: Data[] = [];

    // 1. Super-cluster hulls (bottom layer)
    traces.push(...buildSuperClusterHulls(superClusters));

    // 2. Sub-cluster hulls
    traces.push(...buildClusterHulls(filteredClusters));

    // 3. Article scatter points
    traces.push(...buildArticleTraces(filteredArticles));

    // 4. Centroid stars (top layer)
    const centroidTrace = buildCentroidTrace(filteredClusters);
    if (centroidTrace) traces.push(centroidTrace);

    return { data: traces, layout: buildMapLayout() };
  }, [filteredArticles, filteredClusters, superClusters]);

  if (filteredArticles.length === 0) {
    return (
      <div style={{ textAlign: "center", padding: "2rem", color: "#6b7280" }}>
        No hay artículos para mostrar en el mapa.
      </div>
    );
  }

  return (
    <div data-testid="vista-mapa">
      <PlotlyWrapper
        data={data}
        layout={layout}
        config={{ displayModeBar: true, scrollZoom: true }}
        style={{ width: "100%", minHeight: 500 }}
      />
    </div>
  );
}
