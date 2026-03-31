"""Domain models for the Trendmap pipeline and visualization.

Ported from the design document (Modelos de Datos → Pydantic DTOs, Trendmap
section) and adapted to Pydantic v2 with ``model_config = ConfigDict(...)``,
consistent with ``pipeline_models.py``.

These models represent the full trendmap data structure: clusters with hull
polygons and impact metrics, individual articles with UMAP coordinates,
super-clusters grouped by category, trend timeline entries, and risk signals.

Validates: Requirements 14.1-14.8, 15.1-15.12
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# ── Trendmap Article ──────────────────────────────────────────────────


class TrendmapArticle(BaseModel):
    """Single article/paper positioned in the 2-D UMAP space.

    Validates: Requirements 14.1, 15.3
    """

    model_config = ConfigDict(frozen=False)

    id: str
    title: str
    source: str
    source_type: str = Field(description="news | paper")
    date: str
    score: float
    url: str
    x_embed: float
    y_embed: float
    cluster_id: str


# ── Trendmap Cluster ──────────────────────────────────────────────────


class TrendmapCluster(BaseModel):
    """Cluster produced by HDBSCAN with LLM-generated labels and metrics.

    Validates: Requirements 14.5-14.7, 15.4-15.5, 15.7
    """

    model_config = ConfigDict(frozen=False)

    cluster_id: str
    label: str
    category: str
    summary: str
    keywords: list[str] = Field(default_factory=list)
    relevance: str = Field(description="alta | media | baja")
    item_count: int = 0
    impact_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Impact 0-100")
    horizon_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Horizon 0-1")
    maturity_stage: str = ""
    hull_polygon: list[list[float]] = Field(
        default_factory=list,
        description="Convex hull vertices [[x, y], ...]",
    )
    articles: list[str] = Field(
        default_factory=list,
        description="Article IDs belonging to this cluster",
    )


# ── Super Cluster ─────────────────────────────────────────────────────


class SuperCluster(BaseModel):
    """Aggregation of clusters sharing the same category.

    Validates: Requirements 14.7
    """

    model_config = ConfigDict(frozen=False)

    category: str
    clusters: list[str] = Field(
        default_factory=list,
        description="Cluster IDs in this super-cluster",
    )
    hull_polygon: list[list[float]] = Field(
        default_factory=list,
        description="Combined convex hull [[x, y], ...]",
    )
    total_items: int = 0
    avg_impact: float = 0.0


# ── Trend Entry ───────────────────────────────────────────────────────


class TrendEntry(BaseModel):
    """Single data point in the trend timeline (count + avg score per topic per month).

    Validates: Requirements 14.8
    """

    model_config = ConfigDict(frozen=False)

    date: str
    topic: str
    count: int = 0
    avg_score: float = 0.0


# ── Risk Signal ───────────────────────────────────────────────────────


class RiskSignal(BaseModel):
    """Risk signal detected across clusters.

    Validates: Requirements 14.8
    """

    model_config = ConfigDict(frozen=False)

    type: str
    description: str = ""
    severity: str = Field(default="L", description="H | M | L")
    related_clusters: list[str] = Field(default_factory=list)


# ── Trendmap Meta ─────────────────────────────────────────────────────


class TrendmapMeta(BaseModel):
    """Metadata / KPI summary for a trendmap snapshot.

    Validates: Requirements 14.8, 15.9
    """

    model_config = ConfigDict(frozen=False)

    generated_at: str = ""
    total_articles: int = 0
    total_papers: int = 0
    total_filtered: int = 0
    total_clusters: int = 0
    total_categories: int = 0
    silhouette_score: float = 0.0


# ── Trendmap Response ─────────────────────────────────────────────────


class TrendmapResponse(BaseModel):
    """Full trendmap payload returned by GET /api/trendmap/.

    Contains every section written to trendmap.json: meta, clusters,
    super_clusters, articles, trends, insights, recommendations, and
    risk_signals.

    Validates: Requirements 14.8, 15.1
    """

    model_config = ConfigDict(frozen=False)

    meta: TrendmapMeta = Field(default_factory=TrendmapMeta)
    clusters: list[TrendmapCluster] = Field(default_factory=list)
    super_clusters: list[SuperCluster] = Field(default_factory=list)
    articles: list[TrendmapArticle] = Field(default_factory=list)
    trends: list[TrendEntry] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    risk_signals: list[RiskSignal] = Field(default_factory=list)
