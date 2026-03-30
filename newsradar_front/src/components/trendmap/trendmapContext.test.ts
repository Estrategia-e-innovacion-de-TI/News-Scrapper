/**
 * Unit tests for trendmapContext pure filtering functions.
 *
 * Tests filterArticles and filterClusters with specific examples and edge cases.
 * Validates: Requirements 5.1, 5.5, 5.6
 */
import type { Article, Cluster } from "@/lib/api";
import { filterArticles, filterClusters, TrendmapFilters } from "./trendmapContext";

// ── Test helpers ─────────────────────────────────────────────────────

function makeArticle(overrides: Partial<Article> = {}): Article {
  return {
    id: "a1",
    title: "Test Article",
    url: null,
    source_id: "src1",
    source_type: "news",
    published_at: null,
    relevance_score: 75,
    cluster_id: "c1",
    x_embed: 0,
    y_embed: 0,
    category: "Ciberseguridad",
    summary: null,
    ...overrides,
  };
}

function makeCluster(overrides: Partial<Cluster> = {}): Cluster {
  return {
    cluster_id: "c1",
    label: "Test Cluster",
    category: "Ciberseguridad",
    summary: "Summary",
    keywords: ["test"],
    item_count: 5,
    impact_score: 60,
    horizon_score: 0.5,
    hull_polygon: [],
    avg_score: 70,
    x_embed: 0,
    y_embed: 0,
    relevance: "alta",
    ...overrides,
  };
}

const defaultFilters: TrendmapFilters = {
  showNews: true,
  showPapers: true,
  selectedCategory: null,
  selectedCluster: null,
};

// ── filterArticles tests ─────────────────────────────────────────────

describe("filterArticles", () => {
  const clusters: Cluster[] = [
    makeCluster({ cluster_id: "c1", category: "Ciberseguridad" }),
    makeCluster({ cluster_id: "c2", category: "Inteligencia Artificial" }),
    makeCluster({ cluster_id: "c3", category: "Ciberseguridad" }),
  ];

  const articles: Article[] = [
    makeArticle({ id: "a1", source_type: "news", cluster_id: "c1", category: "Ciberseguridad" }),
    makeArticle({ id: "a2", source_type: "paper", cluster_id: "c2", category: "Inteligencia Artificial" }),
    makeArticle({ id: "a3", source_type: "news", cluster_id: "c3", category: "Ciberseguridad" }),
    makeArticle({ id: "a4", source_type: "paper", cluster_id: "c1", category: "Ciberseguridad" }),
  ];

  it("returns all articles when no filters are active", () => {
    const result = filterArticles(articles, defaultFilters, clusters);
    expect(result).toHaveLength(4);
  });

  it("filters out papers when showPapers is false", () => {
    const filters = { ...defaultFilters, showPapers: false };
    const result = filterArticles(articles, filters, clusters);
    expect(result).toHaveLength(2);
    expect(result.every((a) => a.source_type === "news")).toBe(true);
  });

  it("filters out news when showNews is false", () => {
    const filters = { ...defaultFilters, showNews: false };
    const result = filterArticles(articles, filters, clusters);
    expect(result).toHaveLength(2);
    expect(result.every((a) => a.source_type === "paper")).toBe(true);
  });

  it("returns empty when both source types are disabled", () => {
    const filters = { ...defaultFilters, showNews: false, showPapers: false };
    const result = filterArticles(articles, filters, clusters);
    expect(result).toHaveLength(0);
  });

  it("filters by selectedCategory", () => {
    const filters = { ...defaultFilters, selectedCategory: "Ciberseguridad" };
    const result = filterArticles(articles, filters, clusters);
    // a1 (cat match), a3 (cat match), a4 (cluster c1 is in Ciberseguridad)
    expect(result).toHaveLength(3);
    expect(result.every((a) => a.category === "Ciberseguridad" || ["c1", "c3"].includes(a.cluster_id))).toBe(true);
  });

  it("filters by selectedCluster", () => {
    const filters = { ...defaultFilters, selectedCluster: "c2" };
    const result = filterArticles(articles, filters, clusters);
    expect(result).toHaveLength(1);
    expect(result[0].cluster_id).toBe("c2");
  });

  it("combines source type and category filters", () => {
    const filters: TrendmapFilters = {
      showNews: true,
      showPapers: false,
      selectedCategory: "Ciberseguridad",
      selectedCluster: null,
    };
    const result = filterArticles(articles, filters, clusters);
    // Only news articles in Ciberseguridad: a1, a3
    expect(result).toHaveLength(2);
    expect(result.every((a) => a.source_type === "news")).toBe(true);
  });

  it("combines all filters", () => {
    const filters: TrendmapFilters = {
      showNews: true,
      showPapers: false,
      selectedCategory: "Ciberseguridad",
      selectedCluster: "c1",
    };
    const result = filterArticles(articles, filters, clusters);
    // Only news in Ciberseguridad with cluster c1: a1
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe("a1");
  });

  it("handles empty articles array", () => {
    const result = filterArticles([], defaultFilters, clusters);
    expect(result).toHaveLength(0);
  });

  it("handles empty clusters array", () => {
    const filters = { ...defaultFilters, selectedCategory: "Ciberseguridad" };
    // With no clusters, only articles with matching category directly pass
    const result = filterArticles(articles, filters, []);
    expect(result.every((a) => a.category === "Ciberseguridad")).toBe(true);
  });
});

// ── filterClusters tests ─────────────────────────────────────────────

describe("filterClusters", () => {
  const clusters: Cluster[] = [
    makeCluster({ cluster_id: "c1", category: "Ciberseguridad" }),
    makeCluster({ cluster_id: "c2", category: "Inteligencia Artificial" }),
    makeCluster({ cluster_id: "c3", category: "Ciberseguridad" }),
  ];

  it("returns all clusters when selectedCategory is null", () => {
    const result = filterClusters(clusters, null);
    expect(result).toHaveLength(3);
  });

  it("filters clusters by category", () => {
    const result = filterClusters(clusters, "Ciberseguridad");
    expect(result).toHaveLength(2);
    expect(result.every((c) => c.category === "Ciberseguridad")).toBe(true);
  });

  it("returns empty for non-existent category", () => {
    const result = filterClusters(clusters, "NonExistent");
    expect(result).toHaveLength(0);
  });

  it("handles empty clusters array", () => {
    const result = filterClusters([], "Ciberseguridad");
    expect(result).toHaveLength(0);
  });
});
