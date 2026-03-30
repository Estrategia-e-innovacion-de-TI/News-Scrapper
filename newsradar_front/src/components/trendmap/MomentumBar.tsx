/**
 * MomentumBar — Visual progress bar for trend momentum (0–1 → 0–100%).
 *
 * Validates: Req 6.3 (momentum represented as percentage bar)
 */
import React from "react";

export interface MomentumBarProps {
  /** Momentum value between 0 and 1 */
  value: number;
  label?: string;
}

export default function MomentumBar({ value, label }: MomentumBarProps) {
  const pct = Math.round(Math.min(1, Math.max(0, value)) * 100);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "var(--spacing-sm)",
      }}
      aria-label={label ? `${label}: ${pct}%` : `Momentum: ${pct}%`}
    >
      {label && (
        <span
          style={{
            fontSize: "var(--font-size-xs)",
            color: "var(--color-text-secondary)",
            whiteSpace: "nowrap",
          }}
        >
          {label}
        </span>
      )}
      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        style={{
          flex: 1,
          height: "8px",
          backgroundColor: "var(--color-surface-hover)",
          borderRadius: "var(--radius-sm)",
          overflow: "hidden",
          minWidth: "60px",
        }}
      >
        <div
          data-testid="momentum-fill"
          style={{
            width: `${pct}%`,
            height: "100%",
            backgroundColor: "var(--color-secondary)",
            borderRadius: "var(--radius-sm)",
            transition: "width var(--transition-normal)",
          }}
        />
      </div>
      <span
        data-testid="momentum-pct"
        style={{
          fontSize: "var(--font-size-xs)",
          fontWeight: "var(--font-weight-medium)",
          color: "var(--color-text-secondary)",
          minWidth: "32px",
          textAlign: "right",
        }}
      >
        {pct}%
      </span>
    </div>
  );
}
