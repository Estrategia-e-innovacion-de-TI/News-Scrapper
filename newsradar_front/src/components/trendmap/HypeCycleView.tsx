/**
 * HypeCycleView — Groups trends by maturity_stage into labeled sections.
 *
 * Stage labels:
 *   trigger → "Innovation Trigger"
 *   peak_of_inflated_expectations → "Peak of Inflated Expectations"
 *   trough_of_disillusionment → "Trough of Disillusionment"
 *   slope_of_enlightenment → "Slope of Enlightenment"
 *   plateau_of_productivity → "Plateau of Productivity"
 *
 * Validates: Req 6.4
 */
import React, { useMemo } from "react";
import type { Trend, HypeStage } from "@/lib/api";

export interface HypeCycleViewProps {
  trends: Trend[];
}

const STAGE_ORDER: HypeStage[] = [
  "trigger",
  "peak_of_inflated_expectations",
  "trough_of_disillusionment",
  "slope_of_enlightenment",
  "plateau_of_productivity",
];

const STAGE_LABELS: Record<HypeStage, string> = {
  trigger: "Innovation Trigger",
  peak_of_inflated_expectations: "Peak of Inflated Expectations",
  trough_of_disillusionment: "Trough of Disillusionment",
  slope_of_enlightenment: "Slope of Enlightenment",
  plateau_of_productivity: "Plateau of Productivity",
};

const STAGE_COLORS: Record<HypeStage, string> = {
  trigger: "var(--color-accent)",
  peak_of_inflated_expectations: "var(--color-error)",
  trough_of_disillusionment: "var(--color-warning)",
  slope_of_enlightenment: "var(--color-info)",
  plateau_of_productivity: "var(--color-success)",
};

export default function HypeCycleView({ trends }: HypeCycleViewProps) {
  const grouped = useMemo(() => {
    const map = new Map<HypeStage, Trend[]>();
    for (const stage of STAGE_ORDER) {
      map.set(stage, []);
    }
    for (const t of trends) {
      const list = map.get(t.maturity_stage);
      if (list) list.push(t);
    }
    return map;
  }, [trends]);

  return (
    <section data-testid="hype-cycle-view">
      <h3>Ciclo de Hype</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-lg)" }}>
        {STAGE_ORDER.map((stage) => {
          const stageTrends = grouped.get(stage) ?? [];
          return (
            <div
              key={stage}
              data-testid={`hype-stage-${stage}`}
              style={{
                backgroundColor: "var(--color-surface)",
                borderRadius: "var(--radius-lg)",
                padding: "var(--spacing-md)",
                boxShadow: "var(--shadow-sm)",
                borderTop: `3px solid ${STAGE_COLORS[stage]}`,
              }}
            >
              <h4 style={{ margin: "0 0 var(--spacing-sm) 0" }}>
                {STAGE_LABELS[stage]}
                <span
                  style={{
                    fontSize: "var(--font-size-xs)",
                    color: "var(--color-text-muted)",
                    marginLeft: "var(--spacing-sm)",
                  }}
                >
                  ({stageTrends.length})
                </span>
              </h4>

              {stageTrends.length === 0 ? (
                <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-muted)" }}>
                  Sin tendencias en esta etapa.
                </p>
              ) : (
                <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "var(--spacing-sm)" }}>
                  {stageTrends.map((t, idx) => (
                    <li
                      key={`${t.trend}-${idx}`}
                      data-testid={`hype-trend-${stage}-${idx}`}
                      style={{
                        padding: "var(--spacing-sm)",
                        backgroundColor: "var(--color-background)",
                        borderRadius: "var(--radius-md)",
                        fontSize: "var(--font-size-sm)",
                      }}
                    >
                      <span style={{ fontWeight: "var(--font-weight-medium)" }}>{t.trend}</span>
                      <span style={{ color: "var(--color-text-secondary)", marginLeft: "var(--spacing-sm)" }}>
                        — {t.category}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
