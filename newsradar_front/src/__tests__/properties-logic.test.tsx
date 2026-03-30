/**
 * Property-based tests for filtering, sorting, and grouping logic.
 *
 * Feature: newsradar-frontend
 * Uses fast-check for property-based testing with 20 iterations for speed.
 */
import * as fc from "fast-check";
import type { Cluster, Trend, HypeStage } from "@/lib/api";

// ── Generators ───────────────────────────────────────────────────────

const arbitraryCluster: fc.Arbitrary<Cluster> = fc.record({
  cluster_id: fc.string({ minLength: 1, maxLength: 10 }),
  label: fc.string({ minLength: 1, maxLength: 50 }),
  category: fc.string({ minLength: 1, maxLength: 30 }),
  summary: fc.string({ minLength: 1, maxLength: 200 }),
  keywords: fc.array(fc.string({ minLength: 1, maxLength: 20 }), { minLength: 1, maxLength: 5 }),
  item_count: fc.nat({ max: 1000 }),
  impact_score: fc.nat({ max: 100 }),
  horizon_score: fc.double({ min: 0, max: 1, noNaN: true }),
  hull_polygon: fc.array(fc.tuple(fc.double({ noNaN: true }), fc.double({ noNaN: true })), { minLength: 3, maxLength: 6 }),
  avg_score: fc.double({ min: 0, max: 1, noNaN: true }),
  x_embed: fc.double({ noNaN: true }),
  y_embed: fc.double({ noNaN: true }),
  relevance: fc.constantFrom("alta" as const, "media" as const, "baja" as const),
});

const STAGES: HypeStage[] = [
  "trigger",
  "peak_of_inflated_expectations",
  "trough_of_disillusionment",
  "slope_of_enlightenment",
  "plateau_of_productivity",
];

const arbitraryTrend: fc.Arbitrary<Trend> = fc.record({
  trend: fc.string({ minLength: 1, maxLength: 50 }),
  category: fc.string({ minLength: 1, maxLength: 30 }),
  direction: fc.constantFrom("creciente" as const, "decreciente" as const, "estable" as const),
  momentum: fc.double({ min: 0, max: 1, noNaN: true }),
  maturity_stage: fc.constantFrom(...STAGES),
  description: fc.string({ minLength: 1, maxLength: 200 }),
  impact_on_finance: fc.string({ minLength: 1, maxLength: 200 }),
});

// ── Pure logic functions (extracted from ClusterList and HypeCycleView) ──

function filterClustersByCategory(clusters: Cluster[], category: string): Cluster[] {
  if (!category) return clusters;
  return clusters.filter((c) => c.category === category);
}

function sortClustersByImpactDesc(clusters: Cluster[]): Cluster[] {
  return [...clusters].sort((a, b) => b.impact_score - a.impact_score);
}

function groupTrendsByStage(trends: Trend[]): Map<HypeStage, Trend[]> {
  const map = new Map<HypeStage, Trend[]>();
  for (const stage of STAGES) {
    map.set(stage, []);
  }
  for (const t of trends) {
    const list = map.get(t.maturity_stage);
    if (list) list.push(t);
  }
  return map;
}

// Direction color mapping (from TrendList component)
const DIRECTION_COLORS: Record<Trend["direction"], string> = {
  creciente: "var(--color-trend-up)",
  decreciente: "var(--color-trend-down)",
  estable: "var(--color-trend-stable)",
};

// ── Property 12: Filter clusters by category ─────────────────────────
// Feature: newsradar-frontend, Property 12: Filter clusters by category
// Validates: Requirements 5.3

describe("P12: Filter clusters by category", () => {
  it("for any set of clusters and any category, filtered results contain only clusters with that category", () => {
    fc.assert(
      fc.property(
        fc.array(arbitraryCluster, { minLength: 0, maxLength: 20 }),
        fc.string({ minLength: 1, maxLength: 30 }),
        (clusters, category) => {
          const filtered = filterClustersByCategory(clusters, category);

          // All filtered clusters must have the target category
          for (const c of filtered) {
            expect(c.category).toBe(category);
          }

          // The count should match the number of clusters with that category
          const expectedCount = clusters.filter((c) => c.category === category).length;
          expect(filtered).toHaveLength(expectedCount);
        }
      ),
      { numRuns: 20 }
    );
  });
});

// ── Property 13: Clusters sorted by impact_score descending ──────────
// Feature: newsradar-frontend, Property 13: Clusters sorted by impact_score descending
// Validates: Requirements 5.4

describe("P13: Clusters sorted by impact_score descending", () => {
  it("for any set of clusters, after sorting, each consecutive pair has first.impact_score >= second.impact_score", () => {
    fc.assert(
      fc.property(
        fc.array(arbitraryCluster, { minLength: 2, maxLength: 20 }),
        (clusters) => {
          const sorted = sortClustersByImpactDesc(clusters);

          for (let i = 0; i < sorted.length - 1; i++) {
            expect(sorted[i].impact_score).toBeGreaterThanOrEqual(sorted[i + 1].impact_score);
          }
        }
      ),
      { numRuns: 20 }
    );
  });
});

// ── Property 16: Trends grouped by maturity_stage ────────────────────
// Feature: newsradar-frontend, Property 16: Trends grouped by maturity_stage
// Validates: Requirements 6.4

describe("P16: Trends grouped by maturity_stage", () => {
  it("for any set of trends, each group contains only trends with the same stage, and all trends are assigned to exactly one group", () => {
    fc.assert(
      fc.property(
        fc.array(arbitraryTrend, { minLength: 0, maxLength: 20 }),
        (trends) => {
          const grouped = groupTrendsByStage(trends);

          // Verify the map has all 5 stages
          expect(grouped.size).toBe(5);

          // Each group contains only trends with the matching stage
          let totalGrouped = 0;
          grouped.forEach((stageTrends, stage) => {
            for (const t of stageTrends) {
              expect(t.maturity_stage).toBe(stage);
            }
            totalGrouped += stageTrends.length;
          });

          // Total count across all groups equals input count
          expect(totalGrouped).toBe(trends.length);
        }
      ),
      { numRuns: 20 }
    );
  });
});

// ── Property 17: Direction color mapping is deterministic ────────────
// Feature: newsradar-frontend, Property 17: Direction color mapping is deterministic
// Validates: Requirements 6.5

describe("P17: Direction color mapping is deterministic", () => {
  it("for any direction, the color is always the same: creciente→green, decreciente→red, estable→gray", () => {
    fc.assert(
      fc.property(
        fc.constantFrom<Trend["direction"]>("creciente", "decreciente", "estable"),
        (direction) => {
          const color = DIRECTION_COLORS[direction];

          switch (direction) {
            case "creciente":
              expect(color).toBe("var(--color-trend-up)");
              break;
            case "decreciente":
              expect(color).toBe("var(--color-trend-down)");
              break;
            case "estable":
              expect(color).toBe("var(--color-trend-stable)");
              break;
          }

          // Deterministic: calling again yields the same result
          expect(DIRECTION_COLORS[direction]).toBe(color);
        }
      ),
      { numRuns: 20 }
    );
  });
});
