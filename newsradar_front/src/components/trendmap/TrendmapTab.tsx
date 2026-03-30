/**
 * TrendmapTab — Main container for the Trend Mapping tab.
 *
 * Wraps content in TrendmapProvider, shows a stats bar with KPIs,
 * 6 sub-tab buttons (Resumen, Mapa, Impacto, Hype Cycle, Detalle, Metodología),
 * and a flex layout with chart-area (flex:1) + TrendmapSidebar (340px).
 *
 * Validates: Requirements 4.1, 4.2, 4.3, 4.4
 */
import React, { useState } from "react";
import { TrendmapProvider, useTrendmap } from "@/components/trendmap/trendmapContext";
import TrendmapSidebar from "@/components/trendmap/TrendmapSidebar";
import VistaResumen from "@/components/trendmap/VistaResumen";
import VistaMapa from "@/components/trendmap/VistaMapa";
import VistaImpacto from "@/components/trendmap/VistaImpacto";
import VistaHype from "@/components/trendmap/VistaHype";
import VistaDetalle from "@/components/trendmap/VistaDetalle";
import VistaMetodologia from "@/components/trendmap/VistaMetodologia";
import styles from "./TrendmapTab.module.css";

// ── Sub-tab definitions ──────────────────────────────────────────────

export type SubTabId =
  | "resumen"
  | "mapa"
  | "impacto"
  | "hype"
  | "detalle"
  | "metodologia";

interface SubTabDef {
  id: SubTabId;
  label: string;
}

export const SUB_TABS: SubTabDef[] = [
  { id: "resumen", label: "Resumen" },
  { id: "mapa", label: "Mapa" },
  { id: "impacto", label: "Impacto" },
  { id: "hype", label: "Hype Cycle" },
  { id: "detalle", label: "Detalle" },
  { id: "metodologia", label: "Metodología" },
];

// ── Placeholder view component ───────────────────────────────────────

function ViewPlaceholder({ name }: { name: string }) {
  return (
    <div className={styles.viewPlaceholder} data-testid={`view-${name}`}>
      Vista: {name}
    </div>
  );
}

// ── View resolver ────────────────────────────────────────────────────

function ActiveView({ tabId }: { tabId: SubTabId }) {
  // Placeholder views — will be replaced by real components as they are created
  switch (tabId) {
    case "resumen":
      return <VistaResumen />;
    case "mapa":
      return <VistaMapa />;
    case "impacto":
      return <VistaImpacto />;
    case "hype":
      return <VistaHype />;
    case "detalle":
      return <VistaDetalle />;
    case "metodologia":
      return <VistaMetodologia />;
    default:
      return <ViewPlaceholder name="Resumen" />;
  }
}

// ── Stats bar ────────────────────────────────────────────────────────

function StatsBar() {
  const { filteredArticles, filteredClusters, superClusters, meta } =
    useTrendmap();

  const newsCount = filteredArticles.filter(
    (a) => a.source_type === "news",
  ).length;
  const papersCount = filteredArticles.filter(
    (a) => a.source_type === "paper",
  ).length;
  const categoriesCount = superClusters.length;
  const generatedDate = meta?.generated_at_utc
    ? new Date(meta.generated_at_utc).toLocaleDateString("es-ES", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : "—";

  return (
    <div className={styles.statsBar} role="region" aria-label="Estadísticas del trendmap">
      <span className={styles.stat}>
        📰 Noticias: <span className={styles.statValue}>{newsCount}</span>
      </span>
      <span className={styles.stat}>
        📄 Papers: <span className={styles.statValue}>{papersCount}</span>
      </span>
      <span className={styles.stat}>
        📊 Filtrados: <span className={styles.statValue}>{filteredArticles.length}</span>
      </span>
      <span className={styles.stat}>
        🔗 Clusters: <span className={styles.statValue}>{filteredClusters.length}</span>
      </span>
      <span className={styles.stat}>
        🏷️ Categorías: <span className={styles.statValue}>{categoriesCount}</span>
      </span>
      <span className={styles.stat}>
        📅 Fecha: <span className={styles.statValue}>{generatedDate}</span>
      </span>
    </div>
  );
}

// ── Inner content (needs context) ────────────────────────────────────

function TrendmapTabContent() {
  const [activeTab, setActiveTab] = useState<SubTabId>("resumen");
  const { loading, error } = useTrendmap();

  if (loading) {
    return (
      <div className={styles.loading} role="status">
        Cargando datos del trendmap…
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.error} role="alert">
        <p>Error: {error}</p>
        <button
          type="button"
          className={styles.retryBtn}
          onClick={() => window.location.reload()}
        >
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div className={styles.wrapper}>
      {/* KPI stats bar */}
      <StatsBar />

      {/* Sub-tab navigation */}
      <nav className={styles.tabNav} aria-label="Sub-pestañas del trendmap">
        {SUB_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            className={`${styles.tabBtn} ${activeTab === tab.id ? styles.tabBtnActive : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {/* Chart area + sidebar */}
      <div className={styles.contentRow}>
        <div className={styles.chartArea} role="tabpanel">
          <ActiveView tabId={activeTab} />
        </div>
        <TrendmapSidebar />
      </div>
    </div>
  );
}

// ── Exported component (wraps with provider) ─────────────────────────

export default function TrendmapTab() {
  return (
    <TrendmapProvider>
      <TrendmapTabContent />
    </TrendmapProvider>
  );
}
