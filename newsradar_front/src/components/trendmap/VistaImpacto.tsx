/**
 * VistaImpacto — Bubble chart of cluster impact vs maturity (horizon).
 *
 * X-axis: impact_score (0-100), Y-axis: horizon_score (0-1).
 * Bubble size proportional to sqrt(item_count), colored by CAT_COLORS.
 * Reference lines at X=50 and Y=0.5, maturity stage labels on Y-axis,
 * quadrant annotations, and rich hover tooltip.
 *
 * Exports pure functions `computeBubbleSize` and `getMaturityStage` for testing.
 *
 * Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7
 */
import React, { useMemo } from "react";
import type { Data, Layout } from "plotly.js";
import PlotlyWrapper from "@/components/trendmap/PlotlyWrapper";
import { useTrendmap } from "@/components/trendmap/trendmapContext";
import { CAT_COLORS } from "@/lib/catColors";
import type { Cluster } from "@/lib/api";

// ── Constants ────────────────────────────────────────────────────────

const BUBBLE_SIZE_FACTOR = 14;
const BUBBLE_MIN_SIZE = 25;

/** Maturity stage definitions: horizon_score thresholds → label */
const STAGE_THRESHOLDS: { min: number; max: number; label: string }[] = [
  { min: 0, max: 0.2, label: "Innovation Trigger" },
  { min: 0.2, max: 0.4, label: "Peak of Inflated Expectations" },
  { min: 0.4, max: 0.6, label: "Trough of Disillusionment" },
  { min: 0.6, max: 0.8, label: "Slope of Enlightenment" },
  { min: 0.8, max: 1.0, label: "Plateau of Productivity" },
];

/** Y-axis tick positions and short labels for maturity stages */
const STAGE_TICKS = [
  { y: 0.1, label: "Trigger" },
  { y: 0.3, label: "Peak" },
  { y: 0.5, label: "Trough" },
  { y: 0.7, label: "Slope" },
  { y: 0.9, label: "Plateau" },
];

// ── Pure exported functions ──────────────────────────────────────────

/**
 * Compute bubble size for a cluster based on item_count.
 * Formula: max(BUBBLE_MIN_SIZE, sqrt(item_count) * BUBBLE_SIZE_FACTOR)
 */
export function computeBubbleSize(itemCount: number): number {
  return Math.max(BUBBLE_MIN_SIZE, Math.sqrt(itemCount) * BUBBLE_SIZE_FACTOR);
}

/**
 * Get the maturity stage label for a given horizon_score.
 * Ranges: 0-0.2 Trigger, 0.2-0.4 Peak, 0.4-0.6 Trough, 0.6-0.8 Slope, 0.8-1.0 Plateau.
 */
export function getMaturityStage(horizonScore: number): string {
  for (const stage of STAGE_THRESHOLDS) {
    if (horizonScore >= stage.min && horizonScore < stage.max) {
      return stage.label;
    }
  }
  // Edge case: exactly 1.0 falls into Plateau
  if (horizonScore >= 1.0) return "Plateau of Productivity";
  return "Innovation Trigger";
}

// ── Trace builder ────────────────────────────────────────────────────

function colorForCategory(cat: string | null): string {
  return CAT_COLORS[cat ?? "Otros"] ?? CAT_COLORS["Otros"];
}

/**
 * Build the single scatter trace for the bubble chart.
 * Each cluster becomes a bubble positioned at (impact_score, horizon_score).
 */
export function buildBubbleTrace(clusters: Cluster[]): Data {
  return {
    type: "scatter" as const,
    mode: "markers" as const,
    x: clusters.map((c) => c.impact_score),
    y: clusters.map((c) => c.horizon_score),
    marker: {
      size: clusters.map((c) => computeBubbleSize(c.item_count)),
      color: clusters.map((c) => colorForCategory(c.category)),
      opacity: 0.85,
      line: { width: 2, color: "#fff" },
      sizemode: "area" as const,
    },
    customdata: clusters.map((c) => [
      c.label,
      c.item_count,
      c.avg_score,
      c.impact_score,
      c.horizon_score,
      getMaturityStage(c.horizon_score),
      c.relevance,
    ]),
    hovertemplate:
      "<b>%{customdata[0]}</b><br>" +
      "%{customdata[1]} items · Avg: %{customdata[2]}<br>" +
      "Impact: %{customdata[3]}<br>" +
      "Madurez: %{customdata[4]} (%{customdata[5]})<br>" +
      "Relevancia: %{customdata[6]}" +
      "<extra></extra>",
    showlegend: false,
  } as Data;
}

// ── Layout builder ───────────────────────────────────────────────────

/**
 * Build the Plotly layout with reference lines, stage labels, and quadrant annotations.
 */
export function buildImpactLayout(clusters: Cluster[]): Partial<Layout> {
  // Cluster label annotations (below each bubble)
  const clusterAnnotations = clusters.map((c) => ({
    x: c.impact_score,
    y: c.horizon_score - 0.07,
    text: c.label.replace(/\[.*?\]\s*/, ""),
    showarrow: false,
    font: {
      color: colorForCategory(c.category),
      size: 8,
    },
  }));

  // Quadrant annotations
  const quadrantAnnotations = [
    {
      x: 80,
      y: 0.12,
      text: "Alto Impacto · Emergente",
      showarrow: false,
      font: { color: "#3fb950", size: 9 },
    },
    {
      x: 80,
      y: 0.88,
      text: "Alto Impacto · Maduro",
      showarrow: false,
      font: { color: "#58a6ff", size: 9 },
    },
    {
      x: 20,
      y: 0.12,
      text: "Bajo Impacto · Emergente",
      showarrow: false,
      font: { color: "#8b949e", size: 8 },
    },
  ];

  return {
    paper_bgcolor: "transparent",
    plot_bgcolor: "#fafafa",
    font: { color: "#333" },
    xaxis: {
      title: "Impacto (0-100)",
      gridcolor: "#e5e7eb",
      range: [0, 105],
    },
    yaxis: {
      title: "Madurez",
      gridcolor: "#e5e7eb",
      range: [-0.1, 1.15],
      tickvals: STAGE_TICKS.map((s) => s.y),
      ticktext: STAGE_TICKS.map((s) => s.label),
    },
    margin: { l: 80, r: 20, t: 20, b: 50 },
    hovermode: "closest" as const,
    shapes: [
      // Vertical reference line at X=50
      {
        type: "line" as const,
        x0: 50,
        x1: 50,
        y0: 0,
        y1: 1,
        line: { color: "#d1d5db", dash: "dash" as const },
      },
      // Horizontal reference line at Y=0.5
      {
        type: "line" as const,
        x0: 0,
        x1: 100,
        y0: 0.5,
        y1: 0.5,
        line: { color: "#d1d5db", dash: "dash" as const },
      },
    ],
    annotations: [...clusterAnnotations, ...quadrantAnnotations],
  };
}

// ── Component ────────────────────────────────────────────────────────

export default function VistaImpacto() {
  const { filteredClusters } = useTrendmap();

  const { data, layout } = useMemo(() => {
    const trace = buildBubbleTrace(filteredClusters);
    const plotLayout = buildImpactLayout(filteredClusters);
    return { data: [trace], layout: plotLayout };
  }, [filteredClusters]);

  if (filteredClusters.length === 0) {
    return (
      <div style={{ textAlign: "center", padding: "2rem", color: "#6b7280" }}>
        No hay clusters para mostrar en el gráfico de impacto.
      </div>
    );
  }

  return (
    <div data-testid="vista-impacto">
      <PlotlyWrapper
        data={data}
        layout={layout}
        config={{ displayModeBar: true }}
        style={{ width: "100%", minHeight: 500 }}
      />
    </div>
  );
}
