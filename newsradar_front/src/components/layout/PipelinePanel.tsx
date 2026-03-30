/**
 * PipelinePanel — Control panel for executing and monitoring data pipelines.
 *
 * Features:
 * - 4 buttons to trigger each pipeline type (Trendmap, ARAS, Riesgos, Vigilancia)
 * - Each button calls runPipeline(type) from @/lib/api
 * - Disables the button for a type while its pipeline is running/pending
 * - Shows status badges (pending=yellow, running=blue, completed=green, failed=red)
 * - Table showing recent pipeline runs (fetched via fetchPipelineStatus())
 * - Auto-refreshes status every 10 seconds while any pipeline is running
 *
 * Validates: Req 14.1 (pipeline control panel with buttons)
 * Validates: Req 14.3 (show status, disable while running)
 * Validates: Req 14.6 (history of recent executions)
 */
import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  runPipeline,
  fetchPipelineStatus,
  PipelineRun,
} from "@/lib/api";
import styles from "./PipelinePanel.module.css";

/** Pipeline type definitions with display metadata */
interface PipelineType {
  type: PipelineRun["run_type"];
  label: string;
  icon: string;
}

const PIPELINE_TYPES: PipelineType[] = [
  { type: "trendmap", label: "Trendmap", icon: "📊" },
  { type: "aras", label: "ARAS", icon: "🔍" },
  { type: "riesgos", label: "Riesgos", icon: "⚠️" },
  { type: "vigilancia", label: "Vigilancia", icon: "📡" },
];

const AUTO_REFRESH_MS = 10_000;

/** Map a pipeline status to its CSS badge class */
function badgeClass(status: PipelineRun["status"]): string {
  switch (status) {
    case "pending":
      return styles.badgePending;
    case "running":
      return styles.badgeRunning;
    case "completed":
      return styles.badgeCompleted;
    case "failed":
      return styles.badgeFailed;
    default:
      return "";
  }
}

/** Format an ISO date string for display */
function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("es-CO", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Summarize result_summary for display */
function summarize(run: PipelineRun): string {
  if (run.error_message) return run.error_message;
  if (run.result_summary) {
    const msg = (run.result_summary as Record<string, unknown>).message;
    if (typeof msg === "string") return msg;
    return JSON.stringify(run.result_summary);
  }
  return "—";
}

export default function PipelinePanel() {
  const [open, setOpen] = useState(false);
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runningTypes, setRunningTypes] = useState<Set<PipelineRun["run_type"]>>(new Set());
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /** Fetch the latest pipeline runs from the API */
  const refreshStatus = useCallback(async () => {
    try {
      const data = await fetchPipelineStatus();
      setRuns(data);
      setError(null);

      // Determine which types are currently running/pending
      const active = new Set<PipelineRun["run_type"]>();
      for (const r of data) {
        if (r.status === "pending" || r.status === "running") {
          active.add(r.run_type);
        }
      }
      setRunningTypes(active);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al obtener estado del pipeline");
    }
  }, []);

  /** Start auto-refresh when any pipeline is active */
  useEffect(() => {
    if (open) {
      refreshStatus();
    }
  }, [open, refreshStatus]);

  useEffect(() => {
    if (runningTypes.size > 0 && open) {
      intervalRef.current = setInterval(refreshStatus, AUTO_REFRESH_MS);
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [runningTypes.size, open, refreshStatus]);

  /** Trigger a pipeline execution */
  const handleRun = async (type: PipelineRun["run_type"]) => {
    setLoading(true);
    setError(null);
    try {
      await runPipeline(type);
      await refreshStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al ejecutar pipeline");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.panel} data-testid="pipeline-panel">
      <button
        className={styles.toggleHeader}
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        aria-controls="pipeline-panel-body"
      >
        <span>🚀 Panel de Control — Pipeline</span>
        <span className={`${styles.chevron} ${open ? styles.chevronOpen : ""}`}>
          ▼
        </span>
      </button>

      {open && (
        <div id="pipeline-panel-body" className={styles.body}>
          {error && (
            <div className={styles.errorMessage} role="alert">
              {error}
            </div>
          )}

          {/* Pipeline trigger buttons */}
          <div className={styles.buttonsGrid}>
            {PIPELINE_TYPES.map((pt) => {
              const isActive = runningTypes.has(pt.type);
              return (
                <button
                  key={pt.type}
                  className={styles.pipelineBtn}
                  disabled={isActive || loading}
                  onClick={() => handleRun(pt.type)}
                  data-testid={`pipeline-btn-${pt.type}`}
                  title={
                    isActive
                      ? `${pt.label} está en ejecución`
                      : `Ejecutar pipeline ${pt.label}`
                  }
                >
                  <span className={styles.btnIcon}>{pt.icon}</span>
                  <span className={styles.btnLabel}>{pt.label}</span>
                  {isActive && (
                    <span className={`${styles.badge} ${styles.badgeRunning}`}>
                      en ejecución
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* History table */}
          <div className={styles.historySection}>
            <h3 className={styles.historyTitle}>Historial de ejecuciones</h3>
            {runs.length === 0 ? (
              <p className={styles.emptyMessage}>
                No hay ejecuciones recientes.
              </p>
            ) : (
              <table className={styles.historyTable} data-testid="pipeline-history">
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Tipo</th>
                    <th>Estado</th>
                    <th>Resumen</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => (
                    <tr key={run.id}>
                      <td>{formatDate(run.started_at)}</td>
                      <td>
                        <span className={styles.runTypeBadge}>
                          {run.run_type}
                        </span>
                      </td>
                      <td>
                        <span className={`${styles.badge} ${badgeClass(run.status)}`}>
                          {run.status}
                        </span>
                      </td>
                      <td>
                        <span className={styles.summaryText}>
                          {summarize(run)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
