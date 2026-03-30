/**
 * TrendmapSidebar — Right-side filter panel for the Trendmap tab.
 *
 * - Toggle buttons for Noticias / Papers (both active by default)
 * - Category filter buttons (one per super_cluster + "Todas")
 * - Cluster cards filtered by selected category, showing colored label,
 *   metrics (items, score, impact, maturity, relevance), and keywords
 * - Fixed width 340px, scrollable when content overflows
 *
 * Validates: Requirements 5.1, 5.2, 5.3, 5.4
 */
import React from "react";
import { useTrendmap } from "@/components/trendmap/trendmapContext";
import { CAT_COLORS } from "@/lib/catColors";
import styles from "./TrendmapSidebar.module.css";

const DEFAULT_COLOR = "#8b949e";

export default function TrendmapSidebar() {
  const { filters, setFilters, superClusters, filteredClusters } =
    useTrendmap();

  // Derive unique categories from superClusters
  const categories = superClusters.map((sc) => sc.category);

  const handleToggleNews = () => {
    setFilters({ showNews: !filters.showNews });
  };

  const handleTogglePapers = () => {
    setFilters({ showPapers: !filters.showPapers });
  };

  const handleCategorySelect = (category: string | null) => {
    setFilters({ selectedCategory: category, selectedCluster: null });
  };

  const handleClusterSelect = (clusterId: string) => {
    setFilters({
      selectedCluster:
        filters.selectedCluster === clusterId ? null : clusterId,
    });
  };

  return (
    <aside className={styles.sidebar} aria-label="Filtros del trendmap">
      {/* Source type toggles */}
      <div>
        <h3 className={styles.sectionTitle}>Tipo de fuente</h3>
        <div className={styles.toggleGroup}>
          <button
            type="button"
            className={`${styles.toggleBtn} ${filters.showNews ? styles.toggleBtnActive : ""}`}
            onClick={handleToggleNews}
            aria-pressed={filters.showNews}
          >
            📰 Noticias
          </button>
          <button
            type="button"
            className={`${styles.toggleBtn} ${filters.showPapers ? styles.toggleBtnActive : ""}`}
            onClick={handleTogglePapers}
            aria-pressed={filters.showPapers}
          >
            📄 Papers
          </button>
        </div>
      </div>

      {/* Category filter buttons */}
      <div>
        <h3 className={styles.sectionTitle}>Categoría</h3>
        <div className={styles.categoryGroup}>
          <button
            type="button"
            className={`${styles.categoryBtn} ${filters.selectedCategory === null ? styles.categoryBtnActive : ""}`}
            onClick={() => handleCategorySelect(null)}
          >
            Todas
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              type="button"
              className={`${styles.categoryBtn} ${filters.selectedCategory === cat ? styles.categoryBtnActive : ""}`}
              onClick={() => handleCategorySelect(cat)}
              style={
                filters.selectedCategory === cat
                  ? undefined
                  : { borderColor: CAT_COLORS[cat] ?? DEFAULT_COLOR }
              }
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Cluster cards */}
      <div>
        <h3 className={styles.sectionTitle}>
          Clusters ({filteredClusters.length})
        </h3>
      </div>
      <div className={styles.clusterList}>
        {filteredClusters.map((cluster) => {
          const color = CAT_COLORS[cluster.category] ?? DEFAULT_COLOR;
          const isSelected = filters.selectedCluster === cluster.cluster_id;

          return (
            <div
              key={cluster.cluster_id}
              role="button"
              tabIndex={0}
              className={`${styles.clusterCard} ${isSelected ? styles.clusterCardSelected : ""}`}
              onClick={() => handleClusterSelect(cluster.cluster_id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  handleClusterSelect(cluster.cluster_id);
                }
              }}
              aria-pressed={isSelected}
            >
              {/* Colored category label */}
              <span
                className={styles.categoryLabel}
                style={{ backgroundColor: color }}
              >
                {cluster.category}
              </span>

              {/* Cluster name */}
              <p className={styles.clusterName}>{cluster.label}</p>

              {/* Metrics */}
              <div className={styles.metrics}>
                <span className={styles.metric}>
                  Items: <span className={styles.metricValue}>{cluster.item_count}</span>
                </span>
                <span className={styles.metric}>
                  Score: <span className={styles.metricValue}>{cluster.avg_score.toFixed(1)}</span>
                </span>
                <span className={styles.metric}>
                  Impacto: <span className={styles.metricValue}>{cluster.impact_score.toFixed(1)}</span>
                </span>
                <span className={styles.metric}>
                  Madurez: <span className={styles.metricValue}>{cluster.horizon_score.toFixed(2)}</span>
                </span>
                <span className={styles.metric}>
                  Relevancia: <span className={styles.metricValue}>{cluster.relevance}</span>
                </span>
              </div>

              {/* Keywords */}
              {cluster.keywords.length > 0 && (
                <div className={styles.keywords}>
                  {cluster.keywords.map((kw) => (
                    <span key={kw} className={styles.keyword}>
                      {kw}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </aside>
  );
}
