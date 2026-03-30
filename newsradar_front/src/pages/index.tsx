/**
 * Main page — Uses TabLayout with conditional content rendering per tab.
 *
 * The Riesgos tab renders the full RiesgosTab component with sub-tabs
 * for ARAS and Riesgos Emergentes. Vigilancia renders the subscription form.
 * TrendMap renders the full TrendmapTab with 6 sub-views, sidebar filters,
 * and TrendmapContext providing data to all sub-views.
 * PipelinePanel provides a collapsible section for executing and monitoring pipelines.
 *
 * Validates: Req 1.1, 1.2, 1.3, 2.1-2.6, 3.1-3.5, 4.1, 4.2, 4.3, 5.1-5.5, 6.1-6.5
 * Validates: Req 14.1 (pipeline control panel accessible from interface)
 */
import React from "react";
import TabLayout, {
  TAB_RIESGOS,
  TAB_VIGILANCIA,
  TAB_TRENDMAP,
  TabId,
} from "../components/layout/TabLayout";
import RiesgosTab from "../components/riesgos/RiesgosTab";
import SubscriptionForm from "../components/vigilancia/SubscriptionForm";
import TrendmapTab from "@/components/trendmap/TrendmapTab";
import PipelinePanel from "@/components/layout/PipelinePanel";

function renderTabContent(activeTab: TabId): React.ReactNode {
  switch (activeTab) {
    case TAB_RIESGOS:
      return <RiesgosTab />;
    case TAB_VIGILANCIA:
      return (
        <div data-testid="content-vigilancia">
          <h2>Vigilancia Tecnológica — Suscripciones</h2>
          <SubscriptionForm />
        </div>
      );
    case TAB_TRENDMAP:
      return <TrendmapTab />;
    default:
      return null;
  }
}

export default function Home() {
  return (
    <main>
      <TabLayout>{renderTabContent}</TabLayout>
      <PipelinePanel />
    </main>
  );
}
