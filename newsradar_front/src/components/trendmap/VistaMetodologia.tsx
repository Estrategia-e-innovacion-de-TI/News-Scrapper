/**
 * VistaMetodologia — Methodology documentation view for the trendmap.
 *
 * Displays methodology sections extracted from trendmap metadata:
 * embeddings, clustering, outlier removal, labeling, momentum,
 * maturity_stage, impact_score, horizon_score.
 *
 * Shows configuration parameters (optimal K, silhouette score,
 * embedding model, outlier threshold) when available in meta.
 *
 * Includes a disclaimer note about AI-generated scores.
 *
 * Validates: Requirements 11.1, 11.2, 11.3
 */
import React from "react";
import { useTrendmap } from "@/components/trendmap/trendmapContext";
import styles from "./VistaMetodologia.module.css";

// ── Methodology section labels (display order) ──────────────────────

const METHODOLOGY_SECTIONS: { key: string; label: string }[] = [
  { key: "embeddings", label: "Embeddings" },
  { key: "clustering", label: "Clustering" },
  { key: "outlier_removal", label: "Remoción de Outliers" },
  { key: "labeling", label: "Etiquetado (Labeling)" },
  { key: "momentum", label: "Momentum" },
  { key: "maturity_stage", label: "Etapa de Madurez (Maturity Stage)" },
  { key: "impact_score", label: "Score de Impacto (Impact Score)" },
  { key: "horizon_score", label: "Score de Horizonte (Horizon Score)" },
];

// ── Helper: extract config params from meta ─────────────────────────

interface ConfigParam {
  label: string;
  value: string;
}

/**
 * Extract configuration parameters from TrendmapMeta.
 * The meta object may carry extra fields beyond the TS interface
 * (e.g. config.optimal_k) depending on the backend response.
 */
export function extractConfigParams(meta: Record<string, unknown>): ConfigParam[] {
  const params: ConfigParam[] = [];

  // Try config sub-object first (full trendmap.json shape)
  const config = (meta as Record<string, unknown>).config as
    | Record<string, unknown>
    | undefined;

  if (config) {
    if (config.optimal_k != null) {
      params.push({ label: "K Óptimo", value: String(config.optimal_k) });
    }
    if (config.silhouette_score != null) {
      params.push({ label: "Silhouette Score", value: String(config.silhouette_score) });
    }
    if (config.embedding_model != null) {
      params.push({ label: "Modelo Embeddings", value: String(config.embedding_model) });
    }
    if (config.outlier_threshold != null) {
      params.push({ label: "Threshold Outliers", value: String(config.outlier_threshold) });
    }
  }

  // Fallback: try top-level fields (in case backend flattens them)
  if (params.length === 0) {
    const flat = meta as Record<string, unknown>;
    if (flat.optimal_k != null) {
      params.push({ label: "K Óptimo", value: String(flat.optimal_k) });
    }
    if (flat.silhouette_score != null) {
      params.push({ label: "Silhouette Score", value: String(flat.silhouette_score) });
    }
    if (flat.embedding_model != null) {
      params.push({ label: "Modelo Embeddings", value: String(flat.embedding_model) });
    }
    if (flat.outlier_threshold != null) {
      params.push({ label: "Threshold Outliers", value: String(flat.outlier_threshold) });
    }
  }

  return params;
}

// ── Component ────────────────────────────────────────────────────────

export default function VistaMetodologia() {
  const { meta } = useTrendmap();

  if (!meta) {
    return (
      <div className={styles.empty}>
        No hay metadatos de metodología disponibles.
      </div>
    );
  }

  const methodology = meta.methodology ?? {};
  const configParams = extractConfigParams(meta as unknown as Record<string, unknown>);

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>Metodología del Análisis</h2>

      {/* Configuration parameters */}
      {configParams.length > 0 && (
        <>
          <h3 className={styles.sectionTitle} style={{ marginBottom: "var(--spacing-sm)" }}>
            Parámetros de Configuración
          </h3>
          <div className={styles.configGrid}>
            {configParams.map((p) => (
              <div key={p.label} className={styles.configCard}>
                <div className={styles.configLabel}>{p.label}</div>
                <div className={styles.configValue}>{p.value}</div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Methodology sections */}
      {METHODOLOGY_SECTIONS.map(({ key, label }) => {
        const value = methodology[key];
        if (!value) return null;
        return (
          <div key={key} className={styles.section}>
            <div className={styles.sectionTitle}>{label}</div>
            <div className={styles.sectionBody}>{value}</div>
          </div>
        );
      })}

      {/* Show any extra methodology keys not in the predefined list */}
      {Object.entries(methodology)
        .filter(([key]) => !METHODOLOGY_SECTIONS.some((s) => s.key === key))
        .map(([key, value]) => (
          <div key={key} className={styles.section}>
            <div className={styles.sectionTitle}>{key.replace(/_/g, " ")}</div>
            <div className={styles.sectionBody}>{value}</div>
          </div>
        ))}

      {/* Disclaimer */}
      <div className={styles.disclaimer} role="note">
        <span className={styles.disclaimerIcon}>⚠️</span>
        Los scores son generados por IA y esta herramienta es de exploración.
        No reemplaza el análisis experto.
      </div>
    </div>
  );
}
