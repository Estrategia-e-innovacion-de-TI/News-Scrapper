/**
 * TabLayout — Main shell component with tab navigation.
 *
 * Renders three tabs: "Riesgos", "Vigilancia Tecnológica", "Trend Mapping".
 * "Riesgos" is active by default. Content is rendered via children render-prop
 * or internal content mapping.
 *
 * Validates: Req 1.1, 1.2, 1.3, 1.4
 */
import React, { useState } from "react";
import styles from "./TabLayout.module.css";

/** Tab identifiers — exported for use by other components */
export const TAB_RIESGOS = "riesgos" as const;
export const TAB_VIGILANCIA = "vigilancia" as const;
export const TAB_TRENDMAP = "trendmap" as const;

export type TabId = typeof TAB_RIESGOS | typeof TAB_VIGILANCIA | typeof TAB_TRENDMAP;

export interface TabDef {
  id: TabId;
  label: string;
}

export const TABS: TabDef[] = [
  { id: TAB_RIESGOS, label: "Riesgos" },
  { id: TAB_VIGILANCIA, label: "Vigilancia Tecnológica" },
  { id: TAB_TRENDMAP, label: "Trend Mapping" },
];

export interface TabLayoutProps {
  children?: (activeTab: TabId) => React.ReactNode;
}

export default function TabLayout({ children }: TabLayoutProps) {
  const [activeTab, setActiveTab] = useState<TabId>(TAB_RIESGOS);

  return (
    <div className={styles.wrapper}>
      <div className={styles.tabList} role="tablist" aria-label="Secciones principales">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            id={`tab-${tab.id}`}
            aria-selected={activeTab === tab.id}
            aria-controls={`tabpanel-${tab.id}`}
            className={`${styles.tab} ${activeTab === tab.id ? styles.tabActive : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div
        role="tabpanel"
        id={`tabpanel-${activeTab}`}
        aria-labelledby={`tab-${activeTab}`}
        className={styles.tabPanel}
      >
        {children ? children(activeTab) : null}
      </div>
    </div>
  );
}
