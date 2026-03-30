/**
 * ClusterList — Renders a filterable, sorted list of ClusterCards.
 *
 * Filters by category (dropdown). Sorted by impact_score descending by default.
 * Manages expanded state and filter state internally.
 *
 * Validates: Req 5.2, 5.3, 5.4
 */
import React, { useMemo, useState } from "react";
import type { Cluster } from "@/lib/api";
import ClusterCard from "./ClusterCard";

export interface ClusterListProps {
  clusters: Cluster[];
}

export default function ClusterList({ clusters }: ClusterListProps) {
  const [filterCategory, setFilterCategory] = useState<string>("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const categories = useMemo(() => {
    const cats = new Set(clusters.map((c) => c.category));
    return Array.from(cats).sort();
  }, [clusters]);

  const filtered = useMemo(() => {
    let list = clusters;
    if (filterCategory) {
      list = list.filter((c) => c.category === filterCategory);
    }
    return [...list].sort((a, b) => b.impact_score - a.impact_score);
  }, [clusters, filterCategory]);

  return (
    <section data-testid="cluster-list">
      <h3>Clusters</h3>

      {/* Category filter */}
      <div style={{ marginBottom: "var(--spacing-md)" }}>
        <label htmlFor="cluster-category-filter">Filtrar por categoría:</label>
        <select
          id="cluster-category-filter"
          data-testid="cluster-category-filter"
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
          style={{ maxWidth: "300px" }}
        >
          <option value="">Todas</option>
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {cat}
            </option>
          ))}
        </select>
      </div>

      {/* Cluster cards */}
      {filtered.length === 0 ? (
        <p data-testid="cluster-empty">No se encontraron clusters para esta categoría.</p>
      ) : (
        filtered.map((cluster) => (
          <ClusterCard
            key={cluster.cluster_id}
            cluster={cluster}
            expanded={expandedId === cluster.cluster_id}
            onToggle={() =>
              setExpandedId((prev) =>
                prev === cluster.cluster_id ? null : cluster.cluster_id
              )
            }
          />
        ))
      )}
    </section>
  );
}
