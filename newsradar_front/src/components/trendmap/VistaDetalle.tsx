/**
 * VistaDetalle — Detail table view showing filtered articles sorted by relevance score.
 *
 * Exports pure function `sortArticlesByScore` for independent testing.
 *
 * Columns: #, Score (colored), Tipo (📰/📄), Cluster, Título (link), Fuente
 * Max height 600px with vertical scroll.
 * Filtered article count displayed above the table.
 * Respects sidebar filters via TrendmapContext.
 *
 * Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5
 */
import React, { useMemo } from "react";
import { useTrendmap } from "@/components/trendmap/trendmapContext";
import type { Article } from "@/lib/api";
import styles from "./VistaDetalle.module.css";

// ── Pure sorting function (exported for testing) ─────────────────────

/**
 * Sort articles by relevance_score descending.
 * Returns a new array (does not mutate the input).
 */
export function sortArticlesByScore(articles: Article[]): Article[] {
  return [...articles].sort((a, b) => b.relevance_score - a.relevance_score);
}

// ── Helpers ──────────────────────────────────────────────────────────

function scoreClass(score: number): string {
  if (score >= 70) return styles.scoreGreen;
  if (score >= 55) return styles.scoreYellow;
  return styles.scoreGray;
}

function tipoIcon(sourceType: string): string {
  return sourceType === "news" ? "📰" : "📄";
}

// ── Component ────────────────────────────────────────────────────────

export default function VistaDetalle() {
  const { filteredArticles } = useTrendmap();

  const sorted = useMemo(
    () => sortArticlesByScore(filteredArticles),
    [filteredArticles],
  );

  if (sorted.length === 0) {
    return (
      <div className={styles.empty}>
        No hay artículos que coincidan con los filtros seleccionados.
      </div>
    );
  }

  return (
    <div>
      <div className={styles.countHeader}>
        Artículos filtrados: <span className={styles.countValue}>{sorted.length}</span>
      </div>

      <div className={styles.tableWrapper}>
        <table>
          <thead>
            <tr>
              <th className={styles.colNum}>#</th>
              <th className={styles.colScore}>Score</th>
              <th className={styles.colTipo}>Tipo</th>
              <th>Cluster</th>
              <th>Título</th>
              <th>Fuente</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((article, idx) => (
              <tr key={article.id}>
                <td className={styles.colNum}>{idx + 1}</td>
                <td className={`${styles.colScore} ${scoreClass(article.relevance_score)}`}>
                  {article.relevance_score.toFixed(1)}
                </td>
                <td className={styles.colTipo}>
                  {tipoIcon(article.source_type)}
                </td>
                <td>{article.cluster_id}</td>
                <td>
                  {article.url ? (
                    <a
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={styles.titleLink}
                    >
                      {article.title}
                    </a>
                  ) : (
                    article.title
                  )}
                </td>
                <td>{article.source_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
