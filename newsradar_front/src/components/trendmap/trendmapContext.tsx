/**
 * TrendmapContext — React Context for shared trendmap state and filtering.
 *
 * Provides data (clusters, superClusters, articles, trends, meta),
 * filter state (showNews, showPapers, selectedCategory, selectedCluster),
 * and derived values (filteredArticles, filteredClusters).
 *
 * Fetches data from API Routes on mount.
 * Exports pure filtering functions for independent testing.
 *
 * Validates: Requirements 5.1, 5.5, 5.6
 */
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type {
  Article,
  Cluster,
  SuperCluster,
  Trend,
  TrendmapMeta,
} from "@/lib/api";
import {
  fetchClusters,
  fetchTrends,
  fetchTrendmapMeta,
} from "@/lib/api";

// ── Interfaces ───────────────────────────────────────────────────────

export interface TrendmapFilters {
  showNews: boolean;
  showPapers: boolean;
  selectedCategory: string | null;
  selectedCluster: string | null;
}

export interface TrendmapContextValue {
  filters: TrendmapFilters;
  setFilters: (f: Partial<TrendmapFilters>) => void;
  clusters: Cluster[];
  superClusters: SuperCluster[];
  articles: Article[];
  trends: Trend[];
  meta: TrendmapMeta | null;
  filteredArticles: Article[];
  filteredClusters: Cluster[];
  loading: boolean;
  error: string | null;
}


// ── Pure filtering functions (exported for testing) ──────────────────

/**
 * Filter articles by source type, category, and cluster.
 *
 * - showNews/showPapers: toggle inclusion of news/paper source types
 * - selectedCategory: if set, only include articles whose category matches
 *   OR whose cluster_id belongs to a cluster in that category
 * - selectedCluster: if set, only include articles with matching cluster_id
 */
export function filterArticles(
  articles: Article[],
  filters: TrendmapFilters,
  clusters: Cluster[],
): Article[] {
  let result = articles;

  // Filter by source type
  if (!filters.showNews || !filters.showPapers) {
    result = result.filter((a) => {
      if (a.source_type === "news") return filters.showNews;
      if (a.source_type === "paper") return filters.showPapers;
      return true;
    });
  }

  // Filter by category: match article.category or article.cluster_id → cluster.category
  if (filters.selectedCategory) {
    const clusterIdsInCategory = new Set(
      clusters
        .filter((c) => c.category === filters.selectedCategory)
        .map((c) => c.cluster_id),
    );
    result = result.filter(
      (a) =>
        a.category === filters.selectedCategory ||
        clusterIdsInCategory.has(a.cluster_id),
    );
  }

  // Filter by specific cluster
  if (filters.selectedCluster) {
    result = result.filter((a) => a.cluster_id === filters.selectedCluster);
  }

  return result;
}

/**
 * Filter clusters by selected category.
 * If selectedCategory is null, returns all clusters.
 */
export function filterClusters(
  clusters: Cluster[],
  selectedCategory: string | null,
): Cluster[] {
  if (!selectedCategory) return clusters;
  return clusters.filter((c) => c.category === selectedCategory);
}

// ── Default values ───────────────────────────────────────────────────

const defaultFilters: TrendmapFilters = {
  showNews: true,
  showPapers: true,
  selectedCategory: null,
  selectedCluster: null,
};

const defaultContextValue: TrendmapContextValue = {
  filters: defaultFilters,
  setFilters: () => {},
  clusters: [],
  superClusters: [],
  articles: [],
  trends: [],
  meta: null,
  filteredArticles: [],
  filteredClusters: [],
  loading: true,
  error: null,
};

// ── Context ──────────────────────────────────────────────────────────

const TrendmapContext = createContext<TrendmapContextValue>(defaultContextValue);

// ── Provider ─────────────────────────────────────────────────────────

export function TrendmapProvider({ children }: { children: React.ReactNode }) {
  const [filters, setFiltersState] = useState<TrendmapFilters>(defaultFilters);
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [superClusters, setSuperClusters] = useState<SuperCluster[]>([]);
  const [articles, setArticles] = useState<Article[]>([]);
  const [trends, setTrends] = useState<Trend[]>([]);
  const [meta, setMeta] = useState<TrendmapMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const setFilters = useCallback((partial: Partial<TrendmapFilters>) => {
    setFiltersState((prev) => ({ ...prev, ...partial }));
  }, []);

  // Fetch data on mount
  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        const [clustersRes, trendsRes, metaRes] = await Promise.all([
          fetchClusters(),
          fetchTrends(),
          fetchTrendmapMeta(),
        ]);

        if (cancelled) return;

        setClusters(clustersRes.clusters);
        setSuperClusters(clustersRes.super_clusters);
        setTrends(trendsRes.trends);
        setMeta(metaRes);

        // Articles come from the clusters response if available (ClustersResponseFull),
        // otherwise default to empty array
        const fullRes = clustersRes as { articles?: Article[] };

        // Enrich article categories from cluster data
        const clusterCategoryMap = new Map<string, string>();
        for (const c of clustersRes.clusters) {
          clusterCategoryMap.set(c.cluster_id, c.category);
        }
        const enrichedArticles = (fullRes.articles ?? []).map(a => ({
          ...a,
          category: a.category || clusterCategoryMap.get(a.cluster_id) || null,
        }));
        setArticles(enrichedArticles);
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof Error ? err.message : "Error cargando datos del trendmap",
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadData();
    return () => { cancelled = true; };
  }, []);

  // Derived filtered data
  const filteredClusters = useMemo(
    () => filterClusters(clusters, filters.selectedCategory),
    [clusters, filters.selectedCategory],
  );

  const filteredArticles = useMemo(
    () => filterArticles(articles, filters, clusters),
    [articles, filters, clusters],
  );

  const value: TrendmapContextValue = useMemo(
    () => ({
      filters,
      setFilters,
      clusters,
      superClusters,
      articles,
      trends,
      meta,
      filteredArticles,
      filteredClusters,
      loading,
      error,
    }),
    [
      filters,
      setFilters,
      clusters,
      superClusters,
      articles,
      trends,
      meta,
      filteredArticles,
      filteredClusters,
      loading,
      error,
    ],
  );

  return (
    <TrendmapContext.Provider value={value}>
      {children}
    </TrendmapContext.Provider>
  );
}

// ── Hook ─────────────────────────────────────────────────────────────

export function useTrendmap(): TrendmapContextValue {
  return useContext(TrendmapContext);
}

export default TrendmapContext;
