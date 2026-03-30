/**
 * VistaHype — SVG Hype Cycle curve with trend positioning and summary table.
 *
 * Renders:
 * 1. An SVG with the classic hype cycle curve (5 stages)
 * 2. Trends as colored circles positioned by maturity_stage
 * 3. Vertical stacking to avoid overlap when multiple trends share a stage
 * 4. Labels with name and momentum next to each trend
 * 5. A summary table below: Tendencia, Dirección, Momentum, Etapa, Detalle
 *
 * Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5
 */
import React, { useMemo } from "react";
import { useTrendmap } from "@/components/trendmap/trendmapContext";
import { CAT_COLORS } from "@/lib/catColors";
import type { Trend, HypeStage } from "@/lib/api";
import styles from "./VistaHype.module.css";

// ── Constants ────────────────────────────────────────────────────────

const SVG_WIDTH = 800;
const SVG_HEIGHT = 400;
const CIRCLE_RADIUS = 10;
const STACK_OFFSET = 30;

/** Human-readable labels for each hype stage. */
const STAGE_LABELS: Record<HypeStage, string> = {
  trigger: "Innovation Trigger",
  peak_of_inflated_expectations: "Peak of Inflated Expectations",
  trough_of_disillusionment: "Trough of Disillusionment",
  slope_of_enlightenment: "Slope of Enlightenment",
  plateau_of_productivity: "Plateau of Productivity",
};

/** Direction arrow mapping. */
const DIRECTION_ICON: Record<string, string> = {
  creciente: "↑",
  estable: "→",
  decreciente: "↓",
};

/** Direction CSS class mapping. */
const DIRECTION_CLASS: Record<string, string> = {
  creciente: "dirUp",
  estable: "dirStable",
  decreciente: "dirDown",
};

// ── SVG Hype Cycle curve path ────────────────────────────────────────

/**
 * Smooth cubic Bézier path representing the classic hype cycle curve.
 * Goes: low start → steep rise (trigger) → peak → dip (trough) →
 * gradual rise (slope) → plateau.
 *
 * ViewBox: 0 0 800 400 (y increases downward in SVG, so lower y = higher on curve)
 */
const HYPE_CURVE_PATH =
  "M 20,350 C 60,340 70,300 80,250 C 90,200 130,40 180,30 C 230,20 240,25 260,50 C 280,75 320,280 400,300 C 480,320 520,250 560,200 C 600,150 660,130 720,120 L 780,120";

// ── Stage positions on the curve ─────────────────────────────────────

/**
 * Returns the (x, y) position on the hype cycle curve for a given maturity stage.
 * Exported as a pure function for testing.
 *
 * Stage positions (approximate curve coordinates):
 * - Innovation Trigger: x≈80, y≈250 (rising)
 * - Peak of Inflated Expectations: x≈220, y≈30 (top)
 * - Trough of Disillusionment: x≈400, y≈300 (bottom of dip)
 * - Slope of Enlightenment: x≈560, y≈200 (rising again)
 * - Plateau of Productivity: x≈720, y≈120 (stable)
 */
export function getStagePosition(maturityStage: string): { x: number; y: number } {
  switch (maturityStage) {
    case "trigger":
      return { x: 80, y: 250 };
    case "peak_of_inflated_expectations":
      return { x: 220, y: 30 };
    case "trough_of_disillusionment":
      return { x: 400, y: 300 };
    case "slope_of_enlightenment":
      return { x: 560, y: 200 };
    case "plateau_of_productivity":
      return { x: 720, y: 120 };
    default:
      // Unknown stage — place at center
      return { x: 400, y: 200 };
  }
}

// ── Stage label positions (below the curve for annotations) ──────────

const STAGE_LABEL_POSITIONS: { stage: HypeStage; x: number; y: number }[] = [
  { stage: "trigger", x: 80, y: 380 },
  { stage: "peak_of_inflated_expectations", x: 220, y: 380 },
  { stage: "trough_of_disillusionment", x: 400, y: 380 },
  { stage: "slope_of_enlightenment", x: 560, y: 380 },
  { stage: "plateau_of_productivity", x: 720, y: 380 },
];

// ── Helpers ──────────────────────────────────────────────────────────

/** Get color for a trend based on its category. */
function getTrendColor(category: string): string {
  return CAT_COLORS[category] ?? CAT_COLORS["Otros"] ?? "#8b949e";
}

/** Group trends by maturity_stage and compute stacked y offsets. */
function computeTrendPositions(
  trends: Trend[],
): { trend: Trend; x: number; y: number }[] {
  const stageCount: Record<string, number> = {};
  return trends.map((t) => {
    const base = getStagePosition(t.maturity_stage);
    const count = stageCount[t.maturity_stage] ?? 0;
    stageCount[t.maturity_stage] = count + 1;
    return {
      trend: t,
      x: base.x,
      // Stack upward (lower y in SVG = higher visually)
      y: base.y - count * STACK_OFFSET,
    };
  });
}

// ── SVG Hype Cycle Component ─────────────────────────────────────────

function HypeCycleSVG({ trends }: { trends: Trend[] }) {
  const positioned = useMemo(() => computeTrendPositions(trends), [trends]);

  return (
    <svg
      viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
      width="100%"
      height="auto"
      role="img"
      aria-label="Curva del ciclo de hype con tendencias posicionadas"
    >
      {/* Background */}
      <rect width={SVG_WIDTH} height={SVG_HEIGHT} fill="var(--color-background, #0d1117)" rx="8" />

      {/* Hype cycle curve */}
      <path
        d={HYPE_CURVE_PATH}
        fill="none"
        stroke="var(--color-text-muted, #8b949e)"
        strokeWidth="2.5"
        strokeLinecap="round"
      />

      {/* Stage labels at bottom */}
      {STAGE_LABEL_POSITIONS.map(({ stage, x, y }) => (
        <text
          key={stage}
          x={x}
          y={y}
          textAnchor="middle"
          fill="var(--color-text-secondary, #c9d1d9)"
          fontSize="10"
          fontFamily="Roboto, sans-serif"
        >
          {STAGE_LABELS[stage]}
        </text>
      ))}

      {/* Vertical dashed lines from stage labels to curve */}
      {STAGE_LABEL_POSITIONS.map(({ stage, x }) => {
        const pos = getStagePosition(stage);
        return (
          <line
            key={`line-${stage}`}
            x1={x}
            y1={pos.y + CIRCLE_RADIUS + 2}
            x2={x}
            y2={365}
            stroke="var(--color-text-muted, #8b949e)"
            strokeWidth="0.5"
            strokeDasharray="4 3"
            opacity="0.4"
          />
        );
      })}

      {/* Trend circles and labels */}
      {positioned.map(({ trend, x, y }, idx) => {
        const color = getTrendColor(trend.category);
        return (
          <g key={`${trend.trend}-${idx}`} data-testid={`hype-trend-${idx}`}>
            {/* Circle */}
            <circle
              cx={x}
              cy={y}
              r={CIRCLE_RADIUS}
              fill={color}
              stroke="var(--color-background, #0d1117)"
              strokeWidth="2"
              opacity="0.9"
            />
            {/* Label: name + momentum */}
            <text
              x={x + CIRCLE_RADIUS + 4}
              y={y + 4}
              fill="var(--color-text, #e6edf3)"
              fontSize="10"
              fontFamily="Roboto, sans-serif"
            >
              {trend.trend}
              <tspan fill="var(--color-text-secondary, #c9d1d9)" fontSize="9">
                {" "}({(trend.momentum * 100).toFixed(0)}%)
              </tspan>
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// ── Summary Table Component ──────────────────────────────────────────

function HypeSummaryTable({ trends }: { trends: Trend[] }) {
  return (
    <div className={styles.tableSection}>
      <h3 className={styles.sectionTitle}>Resumen de Tendencias</h3>
      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Tendencia</th>
              <th>Dirección</th>
              <th>Momentum</th>
              <th>Etapa</th>
              <th>Detalle</th>
            </tr>
          </thead>
          <tbody>
            {trends.map((t, idx) => (
              <tr key={`${t.trend}-${idx}`}>
                <td>{t.trend}</td>
                <td>
                  <span className={styles[DIRECTION_CLASS[t.direction] ?? "dirStable"]}>
                    {DIRECTION_ICON[t.direction] ?? "→"}
                  </span>
                </td>
                <td>
                  <div className={styles.momentumBarBg}>
                    <div
                      className={styles.momentumBarFill}
                      style={{ width: `${Math.min(t.momentum * 100, 100)}%` }}
                    />
                  </div>
                  <span style={{ marginLeft: 6, fontSize: "0.75rem" }}>
                    {(t.momentum * 100).toFixed(0)}%
                  </span>
                </td>
                <td>{STAGE_LABELS[t.maturity_stage] ?? t.maturity_stage}</td>
                <td className={styles.descCell} title={t.description}>
                  {t.description}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────────────

export default function VistaHype() {
  const { trends } = useTrendmap();

  if (!trends || trends.length === 0) {
    return (
      <div className={styles.empty} data-testid="vista-hype-empty">
        No hay tendencias disponibles para mostrar el ciclo de hype.
      </div>
    );
  }

  return (
    <div data-testid="vista-hype">
      {/* SVG Hype Cycle Curve */}
      <div className={styles.svgContainer}>
        <h3 className={styles.svgTitle}>Ciclo de Hype — Tendencias</h3>
        <HypeCycleSVG trends={trends} />
      </div>

      {/* Summary Table */}
      <HypeSummaryTable trends={trends} />
    </div>
  );
}
