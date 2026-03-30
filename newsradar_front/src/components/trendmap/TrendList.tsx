/**
 * TrendList — Displays trends with direction color-coding and momentum bars.
 *
 * Shows: name, category, direction (green/red/gray), momentum (MomentumBar),
 * maturity_stage, description, impact_on_finance.
 *
 * Validates: Req 6.2, 6.3, 6.5
 */
import React from "react";
import type { Trend } from "@/lib/api";
import MomentumBar from "./MomentumBar";

export interface TrendListProps {
  trends: Trend[];
}

const DIRECTION_COLORS: Record<Trend["direction"], string> = {
  creciente: "var(--color-trend-up)",
  decreciente: "var(--color-trend-down)",
  estable: "var(--color-trend-stable)",
};

const DIRECTION_LABELS: Record<Trend["direction"], string> = {
  creciente: "↑ Creciente",
  decreciente: "↓ Decreciente",
  estable: "→ Estable",
};

export default function TrendList({ trends }: TrendListProps) {
  if (trends.length === 0) {
    return <p data-testid="trend-list-empty">No hay tendencias disponibles.</p>;
  }

  return (
    <section data-testid="trend-list">
      <h3>Tendencias</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-md)" }}>
        {trends.map((t, idx) => (
          <div
            key={`${t.trend}-${idx}`}
            data-testid={`trend-item-${idx}`}
            style={{
              backgroundColor: "var(--color-surface)",
              borderRadius: "var(--radius-lg)",
              padding: "var(--spacing-md)",
              boxShadow: "var(--shadow-sm)",
              borderLeft: `4px solid ${DIRECTION_COLORS[t.direction]}`,
            }}
          >
            {/* Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--spacing-sm)" }}>
              <h4 data-testid="trend-name" style={{ margin: 0 }}>{t.trend}</h4>
              <div style={{ display: "flex", gap: "var(--spacing-sm)", alignItems: "center" }}>
                <span
                  data-testid="trend-category"
                  style={{
                    fontSize: "var(--font-size-xs)",
                    backgroundColor: "var(--color-surface-hover)",
                    padding: "2px 8px",
                    borderRadius: "var(--radius-sm)",
                  }}
                >
                  {t.category}
                </span>
                <span
                  data-testid="trend-direction"
                  style={{
                    fontSize: "var(--font-size-xs)",
                    fontWeight: "var(--font-weight-medium)",
                    color: DIRECTION_COLORS[t.direction],
                  }}
                >
                  {DIRECTION_LABELS[t.direction]}
                </span>
              </div>
            </div>

            {/* Momentum */}
            <div data-testid="trend-momentum" style={{ marginBottom: "var(--spacing-sm)" }}>
              <MomentumBar value={t.momentum} label="Momentum" />
            </div>

            {/* Maturity stage */}
            <p data-testid="trend-maturity" style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-secondary)", margin: "var(--spacing-xs) 0" }}>
              Etapa: {t.maturity_stage}
            </p>

            {/* Description */}
            <p data-testid="trend-description" style={{ fontSize: "var(--font-size-sm)", margin: "var(--spacing-xs) 0" }}>
              {t.description}
            </p>

            {/* Impact on finance */}
            <p data-testid="trend-impact" style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)", margin: "var(--spacing-xs) 0" }}>
              Impacto financiero: {t.impact_on_finance}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
