/**
 * Property-based tests for UI components.
 *
 * Feature: newsradar-frontend
 * Uses fast-check for property-based testing with 20 iterations for speed.
 */
import React from "react";
import { render, screen, fireEvent, cleanup, within } from "@testing-library/react";
import * as fc from "fast-check";
import TabLayout, {
  TAB_RIESGOS,
  TAB_VIGILANCIA,
  TAB_TRENDMAP,
  TabId,
} from "@/components/layout/TabLayout";
import ClusterCard from "@/components/trendmap/ClusterCard";
import TrendList from "@/components/trendmap/TrendList";
import MomentumBar from "@/components/trendmap/MomentumBar";
import type { Cluster, Trend, HypeStage } from "@/lib/api";

afterEach(() => {
  cleanup();
});

// ── Generators ───────────────────────────────────────────────────────

const arbitraryCluster: fc.Arbitrary<Cluster> = fc.record({
  cluster_id: fc.string({ minLength: 1, maxLength: 10 }),
  label: fc.string({ minLength: 1, maxLength: 50 }).filter((s) => s.trim().length > 0),
  category: fc.string({ minLength: 1, maxLength: 30 }).filter((s) => s.trim().length > 0),
  summary: fc.string({ minLength: 1, maxLength: 200 }).filter((s) => s.trim().length > 0),
  keywords: fc.array(fc.string({ minLength: 1, maxLength: 20 }).filter((s) => s.trim().length > 0), { minLength: 1, maxLength: 5 }),
  item_count: fc.nat({ max: 1000 }),
  impact_score: fc.nat({ max: 100 }),
  horizon_score: fc.double({ min: 0, max: 1, noNaN: true }),
  hull_polygon: fc.array(fc.tuple(fc.double({ noNaN: true }), fc.double({ noNaN: true })), { minLength: 3, maxLength: 6 }),
  avg_score: fc.double({ min: 0, max: 1, noNaN: true }),
  x_embed: fc.double({ noNaN: true }),
  y_embed: fc.double({ noNaN: true }),
  relevance: fc.constantFrom("alta" as const, "media" as const, "baja" as const),
});

const arbitraryTrend: fc.Arbitrary<Trend> = fc.record({
  trend: fc.string({ minLength: 1, maxLength: 50 }).filter((s) => s.trim().length > 0),
  category: fc.string({ minLength: 1, maxLength: 30 }).filter((s) => s.trim().length > 0),
  direction: fc.constantFrom("creciente" as const, "decreciente" as const, "estable" as const),
  momentum: fc.double({ min: 0, max: 1, noNaN: true }),
  maturity_stage: fc.constantFrom(
    "trigger" as const,
    "peak_of_inflated_expectations" as const,
    "trough_of_disillusionment" as const,
    "slope_of_enlightenment" as const,
    "plateau_of_productivity" as const,
  ),
  description: fc.string({ minLength: 1, maxLength: 200 }).filter((s) => s.trim().length > 0),
  impact_on_finance: fc.string({ minLength: 1, maxLength: 200 }).filter((s) => s.trim().length > 0),
});

// ── Property 1: Tab selection shows correct content ──────────────────
// Feature: newsradar-frontend, Property 1: Tab selection shows correct content
// Validates: Requirements 1.2

describe("P1: Tab selection shows correct content", () => {
  const TAB_MAP: Record<TabId, { label: string; testId: string }> = {
    riesgos: { label: "Riesgos", testId: "content-riesgos" },
    vigilancia: { label: "Vigilancia Tecnológica", testId: "content-vigilancia" },
    trendmap: { label: "Trend Mapping", testId: "content-trendmap" },
  };

  it("for any tab, clicking it renders the correct content", () => {
    fc.assert(
      fc.property(
        fc.constantFrom<TabId>("riesgos", "vigilancia", "trendmap"),
        (tabId) => {
          cleanup();
          const { container, unmount } = render(
            <TabLayout>
              {(activeTab: TabId) => (
                <div data-testid={`content-${activeTab}`}>
                  Content for {activeTab}
                </div>
              )}
            </TabLayout>
          );
          const view = within(container);

          // Click the target tab
          const tabButton = view.getByRole("tab", { name: TAB_MAP[tabId].label });
          fireEvent.click(tabButton);

          // The correct content should be rendered
          expect(view.getByTestId(TAB_MAP[tabId].testId)).toBeInTheDocument();

          // The tab should be marked as selected
          expect(tabButton).toHaveAttribute("aria-selected", "true");

          // Other tabs should NOT be selected
          const otherTabs = (Object.keys(TAB_MAP) as TabId[]).filter((t) => t !== tabId);
          for (const other of otherTabs) {
            const otherButton = view.getByRole("tab", { name: TAB_MAP[other].label });
            expect(otherButton).toHaveAttribute("aria-selected", "false");
          }

          unmount();
        }
      ),
      { numRuns: 20 }
    );
  });
});

// ── Property 11: ClusterCard renders all required fields ─────────────
// Feature: newsradar-frontend, Property 11: ClusterCard renders all required fields
// Validates: Requirements 5.2

describe("P11: ClusterCard renders all required fields", () => {
  it("for any Cluster, the card shows label, category, summary, keywords, item_count, impact_score, horizon_score", () => {
    fc.assert(
      fc.property(arbitraryCluster, (cluster) => {
        cleanup();
        const { container, unmount } = render(
          <ClusterCard cluster={cluster} expanded={false} onToggle={() => {}} />
        );
        const view = within(container);

        // Helper: normalize whitespace for comparison (same as toHaveTextContent)
        const norm = (s: string) => s.replace(/\s+/g, " ").trim();

        // label
        expect(norm(view.getByTestId("cluster-label").textContent ?? "")).toBe(norm(cluster.label));
        // category
        expect(norm(view.getByTestId("cluster-category").textContent ?? "")).toBe(norm(cluster.category));
        // summary
        expect(norm(view.getByTestId("cluster-summary").textContent ?? "")).toBe(norm(cluster.summary));
        // keywords — each keyword should appear in the keywords container
        const keywordsText = norm(view.getByTestId("cluster-keywords").textContent ?? "");
        for (const kw of cluster.keywords) {
          expect(keywordsText).toContain(norm(kw));
        }
        // item_count
        expect(view.getByTestId("cluster-item-count").textContent).toContain(
          String(cluster.item_count)
        );
        // impact_score
        expect(view.getByTestId("cluster-impact-score").textContent).toContain(
          String(cluster.impact_score)
        );
        // horizon_score
        expect(view.getByTestId("cluster-horizon-score").textContent).toContain(
          String(cluster.horizon_score)
        );

        unmount();
      }),
      { numRuns: 20 }
    );
  });
});

// ── Property 14: TrendList renders all trend fields ──────────────────
// Feature: newsradar-frontend, Property 14: TrendList renders all trend fields
// Validates: Requirements 6.2

describe("P14: TrendList renders all trend fields", () => {
  it("for any Trend, shows name, category, direction, momentum, maturity_stage, description, impact_on_finance", () => {
    fc.assert(
      fc.property(arbitraryTrend, (trend) => {
        cleanup();
        const { container, unmount } = render(<TrendList trends={[trend]} />);
        const view = within(container);

        // Helper: normalize whitespace for comparison
        const norm = (s: string) => s.replace(/\s+/g, " ").trim();

        // name
        expect(norm(view.getByTestId("trend-name").textContent ?? "")).toBe(norm(trend.trend));
        // category
        expect(norm(view.getByTestId("trend-category").textContent ?? "")).toBe(norm(trend.category));
        // direction — present in the DOM
        expect(view.getByTestId("trend-direction")).toBeInTheDocument();
        // momentum — the MomentumBar should be present
        expect(view.getByTestId("trend-momentum")).toBeInTheDocument();
        // maturity_stage
        expect(view.getByTestId("trend-maturity").textContent).toContain(trend.maturity_stage);
        // description
        expect(norm(view.getByTestId("trend-description").textContent ?? "")).toBe(norm(trend.description));
        // impact_on_finance — rendered with prefix "Impacto financiero: "
        expect(norm(view.getByTestId("trend-impact").textContent ?? "")).toContain(norm(trend.impact_on_finance));

        unmount();
      }),
      { numRuns: 20 }
    );
  });
});

// ── Property 15: MomentumBar scales correctly ────────────────────────
// Feature: newsradar-frontend, Property 15: MomentumBar scales correctly
// Validates: Requirements 6.3

describe("P15: MomentumBar scales correctly", () => {
  it("for any value 0-1, the displayed percentage equals Math.round(value * 100)", () => {
    fc.assert(
      fc.property(
        fc.double({ min: 0, max: 1, noNaN: true }),
        (value) => {
          cleanup();
          const { container, unmount } = render(<MomentumBar value={value} />);
          const view = within(container);

          const expectedPct = Math.round(Math.min(1, Math.max(0, value)) * 100);
          const pctEl = view.getByTestId("momentum-pct");
          expect(pctEl).toHaveTextContent(`${expectedPct}%`);

          // The fill bar width should match
          const fillEl = view.getByTestId("momentum-fill");
          expect(fillEl.style.width).toBe(`${expectedPct}%`);

          // The progressbar aria-valuenow should match
          const progressbar = view.getByRole("progressbar");
          expect(progressbar).toHaveAttribute("aria-valuenow", String(expectedPct));

          unmount();
        }
      ),
      { numRuns: 20 }
    );
  });
});
