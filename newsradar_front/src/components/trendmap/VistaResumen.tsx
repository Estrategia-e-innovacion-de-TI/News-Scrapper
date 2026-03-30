/**
 * VistaResumen — Summary view with 6 KPI cards, 6 Plotly charts,
 * and a cluster summary table.
 *
 * Exports pure computation functions for independent testing:
 *   computeKPIs, groupByMonth, getTopSources, getScoreBySource
 *
 * Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8
 */
import React, { useMemo } from "react";
import type { Data, Layout } from "plotly.js";
import PlotlyWrapper from "@/components/trendmap/PlotlyWrapper";
import { useTrendmap } from "@/components/trendmap/trendmapContext";
import { CAT_COLORS } from "@/lib/catColors";
import type { Article, Cluster } from "@/lib/api";
import styles from "./VistaResumen.module.css";

const DEFAULT_COLOR = "#8b949e";

// ── Pure computation functions (exported for testing) ────────────────

export interface KPIs {
  totalArticles: number;
  avgScore: number;
  clusterCount: number;
  newsCount: number;
  papersCount: number;
  unclusteredCount: number;
}

/**
 * Compute the 6 KPIs from filtered articles and clusters.
 * Validates: Requirement 6.1
 */
export function computeKPIs(articles: Article[], clusters: Cluster[]): KPIs {
  const totalArticles = articles.length;
  const avgScore =
    totalArticles > 0
      ? articles.reduce((sum, a) => sum + a.relevance_score, 0) / totalArticles
      : 0;
  const clusterCount = clusters.length;
  const newsCount = articles.filter((a) => a.source_type === "news").length;
  const papersCount = articles.filter((a) => a.source_type === "paper").length;
  const unclusteredCount = articles.filter(
    (a) => a.cluster_id === "unclustered" || a.cluster_id === "-1",
  ).length;

  return { totalArticles, avgScore, clusterCount, newsCount, papersCount, unclusteredCount };
}

/**
 * Group articles by YYYY-MM from published_at, returning sorted entries.
 * Articles without a valid published_at are excluded.
 * Validates: Requirements 6.2, 6.7
 */
export function groupByMonth(
  articles: Article[],
): { month: string; count: number }[] {
  const map = new Map<string, number>();
  for (const a of articles) {
    if (!a.published_at) continue;
    const d = new Date(a.published_at);
    if (isNaN(d.getTime())) continue;
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    map.set(key, (map.get(key) ?? 0) + 1);
  }
  return Array.from(map.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, count]) => ({ month, count }));
}

/**
 * Get top N sources by article count, sorted descending.
 * Validates: Requirement 6.5
 */
export function getTopSources(
  articles: Article[],
  n: number = 8,
): { source: string; count: number }[] {
  const map = new Map<string, number>();
  for (const a of articles) {
    map.set(a.source_id, (map.get(a.source_id) ?? 0) + 1);
  }
  return Array.from(map.entries())
    .sort(([, a], [, b]) => b - a)
    .slice(0, n)
    .map(([source, count]) => ({ source, count }));
}

/**
 * Compute average relevance_score per source for sources with ≥ minArticles.
 * Returns entries sorted by avg score descending, with color by range.
 * Validates: Requirement 6.6
 */
export function getScoreBySource(
  articles: Article[],
  minArticles: number = 2,
): { source: string; avgScore: number; color: string }[] {
  const map = new Map<string, { sum: number; count: number }>();
  for (const a of articles) {
    const entry = map.get(a.source_id) ?? { sum: 0, count: 0 };
    entry.sum += a.relevance_score;
    entry.count += 1;
    map.set(a.source_id, entry);
  }
  return Array.from(map.entries())
    .filter(([, v]) => v.count >= minArticles)
    .map(([source, v]) => {
      const avg = v.sum / v.count;
      let color = "#8b949e"; // gray < 55
      if (avg >= 70) color = "#3fb950"; // green
      else if (avg >= 55) color = "#d29922"; // yellow
      return { source, avgScore: avg, color };
    })
    .sort((a, b) => b.avgScore - a.avgScore);
}


// ── Chart data builders (private helpers) ────────────────────────────

function buildTimelineData(articles: Article[]): { data: Data[]; layout: Partial<Layout> } {
  const grouped = groupByMonth(articles);
  return {
    data: [
      {
        type: "bar",
        x: grouped.map((g) => g.month),
        y: grouped.map((g) => g.count),
        marker: { color: "#58a6ff" },
      },
    ],
    layout: {
      height: 280,
      margin: { l: 40, r: 20, t: 10, b: 40 },
      xaxis: { title: "Mes", tickangle: -45 },
      yaxis: { title: "Artículos" },
    },
  };
}

function buildScoreHistogramData(articles: Article[]): { data: Data[]; layout: Partial<Layout> } {
  return {
    data: [
      {
        type: "histogram",
        x: articles.map((a) => a.relevance_score),
        xbins: { start: 40, end: 100, size: 5 },
        marker: { color: "#bc8cff" },
      },
    ],
    layout: {
      height: 280,
      margin: { l: 40, r: 20, t: 10, b: 40 },
      xaxis: { title: "Score", range: [40, 100] },
      yaxis: { title: "Frecuencia" },
    },
  };
}

function buildCategoryData(articles: Article[]): { data: Data[]; layout: Partial<Layout> } {
  const map = new Map<string, number>();
  for (const a of articles) {
    const cat = a.category ?? "Otros";
    map.set(cat, (map.get(cat) ?? 0) + 1);
  }
  const entries = Array.from(map.entries()).sort(([, a], [, b]) => b - a);
  const categories = entries.map(([c]) => c);
  const counts = entries.map(([, c]) => c);
  const colors = categories.map((c) => CAT_COLORS[c] ?? DEFAULT_COLOR);

  return {
    data: [
      {
        type: "bar",
        y: categories,
        x: counts,
        orientation: "h",
        marker: { color: colors },
      },
    ],
    layout: {
      height: 280,
      margin: { l: 150, r: 20, t: 10, b: 40 },
      xaxis: { title: "Artículos" },
    },
  };
}

function buildTopSourcesData(articles: Article[]): { data: Data[]; layout: Partial<Layout> } {
  const top = getTopSources(articles, 8);
  return {
    data: [
      {
        type: "bar",
        y: top.map((s) => s.source),
        x: top.map((s) => s.count),
        orientation: "h",
        marker: { color: "#58a6ff" },
      },
    ],
    layout: {
      height: 280,
      margin: { l: 150, r: 20, t: 10, b: 40 },
      xaxis: { title: "Artículos" },
    },
  };
}

function buildScoreBySourceData(articles: Article[]): { data: Data[]; layout: Partial<Layout> } {
  const scored = getScoreBySource(articles, 2);
  return {
    data: [
      {
        type: "bar",
        y: scored.map((s) => s.source),
        x: scored.map((s) => s.avgScore),
        orientation: "h",
        marker: { color: scored.map((s) => s.color) },
      },
    ],
    layout: {
      height: 280,
      margin: { l: 150, r: 20, t: 10, b: 40 },
      xaxis: { title: "Score promedio" },
    },
  };
}

function buildEvolutionData(
  articles: Article[],
  clusters: Cluster[],
): { data: Data[]; layout: Partial<Layout> } {
  // For each cluster, count articles per month
  const traces: Data[] = [];
  for (const cluster of clusters) {
    const clusterArticles = articles.filter((a) => a.cluster_id === cluster.cluster_id);
    if (clusterArticles.length === 0) continue;
    const grouped = groupByMonth(clusterArticles);
    traces.push({
      type: "scatter",
      mode: "lines+markers",
      name: cluster.label,
      x: grouped.map((g) => g.month),
      y: grouped.map((g) => g.count),
      line: { color: CAT_COLORS[cluster.category] ?? DEFAULT_COLOR },
    });
  }
  return {
    data: traces,
    layout: {
      height: 320,
      margin: { l: 40, r: 20, t: 10, b: 40 },
      xaxis: { title: "Mes", tickangle: -45 },
      yaxis: { title: "Artículos" },
      showlegend: true,
      legend: { orientation: "h", y: -0.3 },
    },
  };
}

// ── Component ────────────────────────────────────────────────────────

export default function VistaResumen() {
  const { filteredArticles, filteredClusters } = useTrendmap();

  const kpis = useMemo(
    () => computeKPIs(filteredArticles, filteredClusters),
    [filteredArticles, filteredClusters],
  );

  const timeline = useMemo(() => buildTimelineData(filteredArticles), [filteredArticles]);
  const scoreHist = useMemo(() => buildScoreHistogramData(filteredArticles), [filteredArticles]);
  const categoryChart = useMemo(() => buildCategoryData(filteredArticles), [filteredArticles]);
  const topSources = useMemo(() => buildTopSourcesData(filteredArticles), [filteredArticles]);
  const scoreBySource = useMemo(() => buildScoreBySourceData(filteredArticles), [filteredArticles]);
  const evolution = useMemo(
    () => buildEvolutionData(filteredArticles, filteredClusters),
    [filteredArticles, filteredClusters],
  );

  return (
    <div>
      {/* KPI Cards */}
      <div className={styles.kpiGrid}>
        <div className={styles.kpiCard}>
          <div className={styles.kpiValue}>{kpis.totalArticles}</div>
          <div className={styles.kpiLabel}>Artículos</div>
        </div>
        <div className={styles.kpiCard}>
          <div className={styles.kpiValue}>{kpis.avgScore.toFixed(1)}</div>
          <div className={styles.kpiLabel}>Score Promedio</div>
        </div>
        <div className={styles.kpiCard}>
          <div className={styles.kpiValue}>{kpis.clusterCount}</div>
          <div className={styles.kpiLabel}>Clusters</div>
        </div>
        <div className={styles.kpiCard}>
          <div className={styles.kpiValue}>{kpis.newsCount}</div>
          <div className={styles.kpiLabel}>Noticias</div>
        </div>
        <div className={styles.kpiCard}>
          <div className={styles.kpiValue}>{kpis.papersCount}</div>
          <div className={styles.kpiLabel}>Papers</div>
        </div>
        <div className={styles.kpiCard}>
          <div className={styles.kpiValue}>{kpis.unclusteredCount}</div>
          <div className={styles.kpiLabel}>Sin Cluster</div>
        </div>
      </div>

      {/* Charts */}
      <div className={styles.chartGrid}>
        <div className={styles.chartCard}>
          <div className={styles.chartTitle}>Artículos por mes</div>
          <PlotlyWrapper data={timeline.data} layout={timeline.layout} />
        </div>
        <div className={styles.chartCard}>
          <div className={styles.chartTitle}>Distribución de scores</div>
          <PlotlyWrapper data={scoreHist.data} layout={scoreHist.layout} />
        </div>
        <div className={styles.chartCard}>
          <div className={styles.chartTitle}>Artículos por categoría</div>
          <PlotlyWrapper data={categoryChart.data} layout={categoryChart.layout} />
        </div>
        <div className={styles.chartCard}>
          <div className={styles.chartTitle}>Artículos por fuente (top 8)</div>
          <PlotlyWrapper data={topSources.data} layout={topSources.layout} />
        </div>
        <div className={styles.chartCard}>
          <div className={styles.chartTitle}>Score promedio por fuente</div>
          <PlotlyWrapper data={scoreBySource.data} layout={scoreBySource.layout} />
        </div>
        <div className={`${styles.chartCard} ${styles.chartCardFull}`}>
          <div className={styles.chartTitle}>Evolución por cluster</div>
          <PlotlyWrapper data={evolution.data} layout={evolution.layout} />
        </div>
      </div>

      {/* Cluster summary table */}
      <div className={styles.tableSection}>
        <h3 className={styles.sectionTitle}>Resumen de Clusters</h3>
        <div className={styles.tableWrapper}>
          <table>
            <thead>
              <tr>
                <th>Cluster</th>
                <th>Categoría</th>
                <th>Items</th>
                <th>Avg Score</th>
                <th>Impact</th>
                <th>Madurez</th>
                <th>Relevancia</th>
              </tr>
            </thead>
            <tbody>
              {filteredClusters.map((c) => (
                <tr key={c.cluster_id}>
                  <td>{c.label}</td>
                  <td>{c.category}</td>
                  <td>{c.item_count}</td>
                  <td>{c.avg_score.toFixed(1)}</td>
                  <td>{c.impact_score.toFixed(1)}</td>
                  <td>{c.horizon_score.toFixed(2)}</td>
                  <td>
                    <span
                      className={
                        c.relevance === "alta"
                          ? styles.relevanceAlta
                          : c.relevance === "media"
                            ? styles.relevanceMedia
                            : styles.relevanceBaja
                      }
                    >
                      {c.relevance}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
