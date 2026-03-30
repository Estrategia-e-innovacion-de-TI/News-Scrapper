/**
 * ClusterCard — Expandable card showing cluster details.
 *
 * Displays label, category, summary, keywords, item_count, impact_score,
 * horizon_score. Expands on click to show hull_polygon and embedding coords.
 *
 * Validates: Req 5.2, 5.5
 */
import React from "react";
import type { Cluster } from "@/lib/api";

export interface ClusterCardProps {
  cluster: Cluster;
  expanded: boolean;
  onToggle: () => void;
}

export default function ClusterCard({ cluster, expanded, onToggle }: ClusterCardProps) {
  return (
    <div
      data-testid={`cluster-card-${cluster.cluster_id}`}
      onClick={onToggle}
      role="button"
      tabIndex={0}
      aria-expanded={expanded}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onToggle();
        }
      }}
      style={{
        backgroundColor: "var(--color-surface)",
        borderRadius: "var(--radius-lg)",
        padding: "var(--spacing-md)",
        marginBottom: "var(--spacing-sm)",
        boxShadow: "var(--shadow-sm)",
        cursor: "pointer",
        transition: "box-shadow var(--transition-fast)",
        border: expanded ? "1px solid var(--color-secondary)" : "1px solid transparent",
      }}
    >
      {/* Header row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h4 data-testid="cluster-label" style={{ margin: 0 }}>{cluster.label}</h4>
        <span
          data-testid="cluster-category"
          style={{
            fontSize: "var(--font-size-xs)",
            backgroundColor: "var(--color-primary)",
            color: "var(--color-text-inverse)",
            padding: "2px 8px",
            borderRadius: "var(--radius-sm)",
          }}
        >
          {cluster.category}
        </span>
      </div>

      {/* Summary */}
      <p data-testid="cluster-summary" style={{ margin: "var(--spacing-sm) 0", fontSize: "var(--font-size-sm)" }}>
        {cluster.summary}
      </p>

      {/* Keywords */}
      <div data-testid="cluster-keywords" style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginBottom: "var(--spacing-sm)" }}>
        {cluster.keywords.map((kw) => (
          <span
            key={kw}
            style={{
              fontSize: "var(--font-size-xs)",
              backgroundColor: "var(--color-surface-hover)",
              padding: "2px 6px",
              borderRadius: "var(--radius-sm)",
            }}
          >
            {kw}
          </span>
        ))}
      </div>

      {/* Metrics row */}
      <div style={{ display: "flex", gap: "var(--spacing-md)", fontSize: "var(--font-size-xs)", color: "var(--color-text-secondary)" }}>
        <span data-testid="cluster-item-count">Artículos: {cluster.item_count}</span>
        <span data-testid="cluster-impact-score">Impacto: {cluster.impact_score}</span>
        <span data-testid="cluster-horizon-score">Horizonte: {cluster.horizon_score}</span>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div data-testid="cluster-details" style={{ marginTop: "var(--spacing-md)", borderTop: "1px solid var(--color-surface-hover)", paddingTop: "var(--spacing-md)" }}>
          <div style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-secondary)" }}>
            <p data-testid="cluster-embedding" style={{ margin: "var(--spacing-xs) 0" }}>
              Embedding: ({cluster.x_embed.toFixed(4)}, {cluster.y_embed.toFixed(4)})
            </p>
            <details>
              <summary style={{ cursor: "pointer" }}>Hull Polygon ({cluster.hull_polygon.length} puntos)</summary>
              <pre data-testid="cluster-hull" style={{ fontSize: "var(--font-size-xs)", overflow: "auto", maxHeight: "120px" }}>
                {JSON.stringify(cluster.hull_polygon, null, 2)}
              </pre>
            </details>
          </div>
        </div>
      )}
    </div>
  );
}
