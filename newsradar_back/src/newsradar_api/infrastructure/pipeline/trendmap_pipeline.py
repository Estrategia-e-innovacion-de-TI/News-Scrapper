"""Trendmap data pipeline — generates trendmap.json from JSONL sources.

Ported from ``news_radar_mvp/trendmap/scripts/build_trendmap.py`` and
``compute_corpus_stats.py``.  Implements the full 9-step pipeline:

1. Load articles and papers from JSONL, filter by year/score/off-topic
2. Compute embeddings with Bedrock Titan Embed v2 (cache in JSONL)
3. Fallback to TF-IDF if Bedrock unavailable
4. Project to 2D with UMAP (metric=cosine) + PCA
5. Cluster with HDBSCAN
6. Label clusters with Claude Haiku
7. Compute hull_polygon, impact_score, horizon_score
8. Generate super_clusters by category
9. Write trendmap.json

Validates: Requirements 14.1-14.8
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from newsradar_api.domain.model.trendmap_models import (
    RiskSignal,
    SuperCluster,
    TrendEntry,
    TrendmapArticle,
    TrendmapCluster,
    TrendmapMeta,
    TrendmapResponse,
)

logger = logging.getLogger("newsradar.trendmap")

# Off-topic keywords to filter out
_OFF_TOPIC = {
    "yolo", "3d city", "occupancy", "robot manipulation", "drone target",
    "soap opera", "lululemon", "biodesign", "humanoid robot", "kid-size",
    "window-washing", "emergency vehicle", "rocket turbine", "space power",
    "child safety", "creator revenue", "joint ev project", "robotaxi",
    "optical clock", "dirac operator", "cosmic coincidence", "wine-glass",
    "dark energy", "black hole", "brickwork circuit", "biological membrane",
    "hall viscosity", "cpt violation", "baryon asymmetry", "majorana",
}


# ── Helpers ───────────────────────────────────────────────────────────


def _sha256(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()[:16]


def _parse_date(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


def _load_jsonl(
    path: Path,
    min_year: int = 2024,
    min_score: int = 55,
) -> list[dict]:
    """Load JSONL, filtering old items, low-relevance, and off-topic (Req 14.1)."""
    items: list[dict] = []
    if not path.exists():
        logger.warning("JSONL file not found: %s", path)
        return items

    skipped_date = skipped_score = skipped_topic = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                doc = json.loads(line)
                pa = doc.get("published_at", "")
                if pa and pa[:4].isdigit() and int(pa[:4]) < min_year:
                    skipped_date += 1
                    continue
                score = doc.get("relevance_score") or 0
                if score <= min_score:
                    skipped_score += 1
                    continue
                title_lower = doc.get("title", "").lower()
                if any(kw in title_lower for kw in _OFF_TOPIC):
                    skipped_topic += 1
                    continue
                items.append(doc)
            except json.JSONDecodeError:
                pass

    logger.info(
        "Loaded %s: kept %d, skipped %d (date), %d (score≤%d), %d (off-topic)",
        path.name, len(items), skipped_date, skipped_score, min_score, skipped_topic,
    )
    return items


def _embed_texts_tfidf(texts: list[str]) -> list[list[float]]:
    """Fallback: TF-IDF pseudo-embeddings (Req 14.3)."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    vectorizer = TfidfVectorizer(max_features=256, stop_words="english")
    matrix = vectorizer.fit_transform(texts)
    return matrix.toarray().tolist()


def _project_umap(
    embeddings: list[list[float]],
    n_neighbors: int = 10,
    min_dist: float = 0.3,
    random_state: int = 42,
    spread: float = 2.0,
) -> list[tuple[float, float]]:
    """Project embeddings to 2D with UMAP + PCA (Req 14.4)."""
    import umap

    valid_mask = np.array([len(e) > 0 for e in embeddings])
    if valid_mask.sum() < 3:
        return [(0.0, 0.0)] * len(embeddings)

    max_dim = max(len(e) for e in embeddings if len(e) > 0)
    padded = np.zeros((len(embeddings), max_dim))
    for i, e in enumerate(embeddings):
        if len(e) > 0:
            padded[i, : len(e)] = e

    # PCA to reduce noise before UMAP
    from sklearn.decomposition import PCA

    n_pca = min(50, padded.shape[1], padded.shape[0] - 1)
    if n_pca >= 2:
        padded = PCA(n_components=n_pca, random_state=random_state).fit_transform(padded)

    effective_neighbors = min(n_neighbors, int(valid_mask.sum()) - 1)
    effective_neighbors = max(effective_neighbors, 2)

    reducer = umap.UMAP(
        n_neighbors=effective_neighbors,
        min_dist=min_dist,
        spread=spread,
        n_components=2,
        metric="cosine",
        random_state=random_state,
    )
    coords = reducer.fit_transform(padded)
    return [(float(coords[i, 0]), float(coords[i, 1])) for i in range(len(embeddings))]


def _compute_hull(
    points: list[tuple[float, float]],
    percentile: float = 85,
) -> list[list[float]]:
    """Compute convex hull with trimming at *percentile* (Req 14.6)."""
    if len(points) < 2:
        if len(points) == 1:
            x, y = points[0]
            r = 0.05
            return [
                [x + r * math.cos(a), y + r * math.sin(a)]
                for a in np.linspace(0, 2 * math.pi, 16)
            ]
        return []

    if len(points) < 3:
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
        r = 0.1
        return [
            [cx + r * math.cos(a), cy + r * math.sin(a)]
            for a in np.linspace(0, 2 * math.pi, 16)
        ]

    pts = np.array(points)
    centroid = pts.mean(axis=0)
    dists = np.linalg.norm(pts - centroid, axis=1)
    if len(pts) > 5:
        threshold = np.percentile(dists, percentile)
        pts = pts[dists <= threshold]

    if len(pts) < 3:
        pts = np.array(points)

    from scipy.spatial import ConvexHull

    try:
        hull = ConvexHull(pts)
        return [[float(pts[v, 0]), float(pts[v, 1])] for v in hull.vertices]
    except Exception:
        return []


def _compute_impact(articles: list[dict]) -> float:
    """Compute impact score 0-100 for a cluster (Req 14.6)."""
    if not articles:
        return 0.0

    scores = [a.get("relevance_score", 0) for a in articles]
    avg_score = float(np.mean(scores)) if scores else 0

    volume = min(math.log1p(len(articles)) / math.log1p(100), 1.0) * 100

    now = datetime.utcnow()
    days_list: list[float] = []
    for a in articles:
        d = _parse_date(a.get("published_at"))
        if d:
            days_list.append((now - d).days)
    median_days = float(np.median(days_list)) if days_list else 30
    recency = max(0, 100 - median_days * 3)

    impact = 0.45 * avg_score + 0.25 * volume + 0.20 * recency + 0.10 * 10
    return round(min(max(impact, 0), 100), 1)


def _compute_horizon(impact_score: float, item_count: int) -> tuple[float, str]:
    """Compute horizon score 0-1 and Gartner maturity stage (Req 14.6)."""
    volume_factor = min(item_count / 30, 1.0)
    impact_signal = impact_score / 100.0

    if impact_signal >= 0.7 and volume_factor >= 0.5:
        return 0.7, "slope_of_enlightenment"
    elif impact_signal >= 0.6:
        return 0.3, "peak_of_inflated_expectations"
    elif volume_factor >= 0.3:
        return 0.5, "trough_of_disillusionment"
    elif impact_signal >= 0.4:
        return 0.1, "innovation_trigger"
    else:
        return 0.2, "trough_of_disillusionment"


def _label_cluster_fallback(titles: list[str]) -> tuple[str, str, str, list[str], str]:
    """Fallback cluster labelling using word frequency."""
    all_words: list[str] = []
    for t in titles:
        all_words.extend(w.lower() for w in t.split() if len(w) >= 4)
    common = [w for w, _ in Counter(all_words).most_common(5)]
    label = " / ".join(common[:3]) if common else "Cluster"
    return label, "Otros", "", common[:5], "media"


def _label_cluster_with_llm(
    titles: list[str],
    bedrock_adapter: Any | None = None,
) -> tuple[str, str, str, list[str], str]:
    """Label a cluster using Claude Haiku (Req 14.5).

    Returns (label, category, summary, keywords, relevance).
    """
    if bedrock_adapter is None:
        return _label_cluster_fallback(titles)

    titles_text = "\n".join(f"- {t}" for t in titles[:20])
    prompt = (
        "You are a tech trend analyst. Given these article titles from a semantic cluster,\n"
        "generate a precise categorization.\n\n"
        f"Titles:\n{titles_text}\n\n"
        "Respond ONLY with this JSON:\n"
        '{\n'
        '  "label": "<descriptive name, 3-6 words, in Spanish>",\n'
        '  "category": "<one of: Ciberseguridad|Inteligencia Artificial|Blockchain/Cripto|'
        'Fintech/Banca Digital|Cloud/Datos|Regulación|Computación Cuántica|Innovación General>",\n'
        '  "summary": "<1-2 sentence summary in Spanish>",\n'
        '  "keywords": ["kw1","kw2","kw3","kw4","kw5"],\n'
        '  "relevance": "<alta|media|baja> for fintech/cybersecurity sector"\n'
        "}"
    )

    try:
        text = bedrock_adapter.invoke_claude(prompt, max_tokens=300)
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            parsed = json.loads(m.group())
            label = parsed.get("label", "Cluster")
            category = parsed.get("category", "Otros")
            return (
                f"[{category}] {label}" if category else label,
                category,
                parsed.get("summary", ""),
                parsed.get("keywords", [])[:5],
                parsed.get("relevance", "media"),
            )
    except Exception as exc:
        logger.debug("LLM cluster labeling failed: %s", exc)

    return _label_cluster_fallback(titles)


# ── TrendmapPipeline ─────────────────────────────────────────────────


class TrendmapPipeline:
    """Generates a complete trendmap dataset from JSONL article sources.

    Implements the 9-step pipeline described in the design document:
    1. Load & filter articles/papers from JSONL
    2. Compute embeddings (Bedrock Titan Embed v2 with JSONL cache)
    3. Fallback to TF-IDF if Bedrock unavailable
    4. Project to 2D with UMAP (cosine) + PCA
    5. Cluster with HDBSCAN
    6. Label clusters with Claude Haiku
    7. Compute hull_polygon, impact_score, horizon_score
    8. Generate super_clusters by category
    9. Write trendmap.json

    Validates: Requirements 14.1-14.8
    """

    def __init__(
        self,
        articles_path: str | Path = "out/articles.jsonl",
        papers_path: str | Path = "out/articles_papers.jsonl",
        output_dir: str | Path = "data/trendmap",
        min_year: int = 2024,
        min_score: int = 55,
    ) -> None:
        self.articles_path = Path(articles_path)
        self.papers_path = Path(papers_path)
        self.output_dir = Path(output_dir)
        self.min_year = min_year
        self.min_score = min_score

    def generate(self, config: dict[str, Any] | None = None) -> TrendmapResponse:
        """Run the full trendmap pipeline and return a :class:`TrendmapResponse`.

        Parameters
        ----------
        config : dict | None
            Optional configuration overrides (umap, hull, embeddings settings).

        Returns
        -------
        TrendmapResponse
            Complete trendmap data ready for API response or JSON serialisation.
        """
        config = config or {}

        # ── Step 1: Load & filter ──
        articles_raw = _load_jsonl(self.articles_path, self.min_year, self.min_score)
        papers_raw = _load_jsonl(self.papers_path, self.min_year, self.min_score)

        for a in articles_raw:
            a["_source_type"] = "news"
        for a in papers_raw:
            a["_source_type"] = "paper"
        all_articles = articles_raw + papers_raw

        logger.info(
            "Loaded %d news + %d papers = %d total",
            len(articles_raw), len(papers_raw), len(all_articles),
        )

        if len(all_articles) < 3:
            logger.warning("Too few articles (%d) for trendmap", len(all_articles))
            return TrendmapResponse(
                meta=TrendmapMeta(
                    generated_at=datetime.utcnow().isoformat() + "Z",
                    total_articles=len(articles_raw),
                    total_papers=len(papers_raw),
                    total_filtered=len(all_articles),
                ),
            )

        for i, a in enumerate(all_articles):
            a["article_id"] = _sha256(a.get("url", "") or a.get("title", str(i)))

        # ── Step 2-3: Embeddings (Bedrock with TF-IDF fallback) ──
        texts = [
            a.get("title", "") + "\n\n" + (a.get("excerpt", "") or a.get("text", "")[:500])
            for a in all_articles
        ]

        bedrock_adapter = None
        embeddings: list[list[float]] = []
        embedding_method = "tfidf"

        try:
            from newsradar_api.infrastructure.driven_adapters.bedrock_adapter import BedrockAdapter

            adapter = BedrockAdapter(
                cache_dir=self.output_dir / "embeddings_cache",
            )
            if adapter.is_available():
                embeddings = adapter.get_embeddings(texts)
                bedrock_adapter = adapter
                embedding_method = "bedrock_titan_v2"
                logger.info("Bedrock embeddings computed")
        except Exception as exc:
            logger.warning("Bedrock unavailable (%s), using TF-IDF fallback", exc)

        if not embeddings or all(len(e) == 0 for e in embeddings):
            embeddings = _embed_texts_tfidf(texts)
            embedding_method = "tfidf"
            logger.info("TF-IDF fallback embeddings computed")

        # ── Step 4: UMAP projection ──
        umap_config = config.get("umap", {})
        coords = _project_umap(
            embeddings,
            n_neighbors=umap_config.get("n_neighbors", 10),
            min_dist=umap_config.get("min_dist", 0.3),
            random_state=umap_config.get("random_state", 42),
            spread=umap_config.get("spread", 2.0),
        )
        for i, (x, y) in enumerate(coords):
            all_articles[i]["x_embed"] = round(x, 4)
            all_articles[i]["y_embed"] = round(y, 4)

        # ── Step 5: HDBSCAN clustering ──
        emb_array = np.array([
            e if len(e) > 0 else [0.0] * (len(embeddings[0]) if embeddings[0] else 1)
            for e in embeddings
        ])

        from sklearn.decomposition import PCA

        n_pca = min(50, emb_array.shape[1], emb_array.shape[0] - 1)
        if n_pca >= 2:
            emb_reduced = PCA(n_components=n_pca, random_state=42).fit_transform(emb_array)
        else:
            emb_reduced = emb_array

        import hdbscan

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=max(4, len(all_articles) // 40),
            min_samples=3,
            metric="euclidean",
            cluster_selection_method="eom",
        )
        labels = clusterer.fit_predict(emb_reduced)
        n_found = len(set(l for l in labels if l >= 0))
        n_noise = sum(1 for l in labels if l < 0)

        # Silhouette score
        silhouette = 0.0
        if n_found >= 2:
            mask = labels >= 0
            if mask.sum() > n_found:
                from sklearn.metrics import silhouette_score

                silhouette = float(silhouette_score(emb_reduced[mask], labels[mask]))

        logger.info(
            "HDBSCAN: %d clusters, %d noise, silhouette=%.3f",
            n_found, n_noise, silhouette,
        )

        # Map articles to clusters
        cluster_article_map: dict[str, list[dict]] = {}
        for i, label in enumerate(labels):
            cid = f"cluster_{label}" if label >= 0 else "unclustered"
            all_articles[i]["cluster_id"] = cid
            cluster_article_map.setdefault(cid, []).append(all_articles[i])

        # ── Step 6: Label clusters with LLM ──
        clusters_data: list[dict[str, Any]] = []
        for cid, cl_articles in sorted(cluster_article_map.items()):
            if cid == "unclustered":
                continue
            titles = [a.get("title", "")[:80] for a in cl_articles[:20]]
            label, category, summary, keywords, relevance = _label_cluster_with_llm(
                titles, bedrock_adapter
            )
            clusters_data.append({
                "cluster_id": cid,
                "label": label,
                "category": category,
                "summary": summary,
                "keywords": keywords,
                "relevance": relevance,
                "articles": cl_articles,
            })

        # ── Step 7: Compute hulls, impact, horizon ──
        clusters_out: list[TrendmapCluster] = []
        for cl in clusters_data:
            cid = cl["cluster_id"]
            cl_articles = cl["articles"]
            cl_coords = [
                (a["x_embed"], a["y_embed"])
                for a in cl_articles
                if "x_embed" in a
            ]

            hull_poly = _compute_hull(cl_coords)
            impact = _compute_impact(cl_articles)
            horizon, maturity_stage = _compute_horizon(impact, len(cl_articles))

            clusters_out.append(
                TrendmapCluster(
                    cluster_id=cid,
                    label=cl["label"],
                    category=cl["category"],
                    summary=cl["summary"],
                    keywords=cl["keywords"][:6],
                    relevance=cl["relevance"],
                    item_count=len(cl_articles),
                    impact_score=impact,
                    horizon_score=horizon,
                    maturity_stage=maturity_stage,
                    hull_polygon=hull_poly,
                    articles=[a.get("article_id", "") for a in cl_articles],
                )
            )

        # ── Step 8: Super-clusters by category ──
        category_map: dict[str, list[TrendmapCluster]] = {}
        for cl in clusters_out:
            category_map.setdefault(cl.category, []).append(cl)

        super_clusters_out: list[SuperCluster] = []
        for cat, sub_clusters in category_map.items():
            all_cat_articles: list[dict] = []
            for sc in sub_clusters:
                all_cat_articles.extend(
                    cluster_article_map.get(sc.cluster_id, [])
                )
            cat_coords = [
                (a["x_embed"], a["y_embed"])
                for a in all_cat_articles
                if "x_embed" in a
            ]
            cat_hull = _compute_hull(cat_coords) if len(cat_coords) >= 3 else []
            avg_impact = (
                float(np.mean([sc.impact_score for sc in sub_clusters]))
                if sub_clusters
                else 0.0
            )

            super_clusters_out.append(
                SuperCluster(
                    category=cat,
                    clusters=[sc.cluster_id for sc in sub_clusters],
                    hull_polygon=cat_hull,
                    total_items=len(all_cat_articles),
                    avg_impact=round(avg_impact, 1),
                )
            )

        # ── Step 9: Build articles list and trends ──
        articles_out: list[TrendmapArticle] = []
        for a in all_articles:
            articles_out.append(
                TrendmapArticle(
                    id=a.get("article_id", ""),
                    title=a.get("title", ""),
                    source=a.get("source_id", ""),
                    source_type=a.get("_source_type", "unknown"),
                    date=a.get("published_at", ""),
                    score=float(a.get("relevance_score", 0)),
                    url=a.get("url", ""),
                    x_embed=a.get("x_embed", 0.0),
                    y_embed=a.get("y_embed", 0.0),
                    cluster_id=a.get("cluster_id", "unclustered"),
                )
            )

        # Trends from super-clusters
        trends_out: list[TrendEntry] = []
        for sc in super_clusters_out:
            sub_cls = [c for c in clusters_out if c.category == sc.category]
            avg_score = (
                float(np.mean([c.impact_score for c in sub_cls]))
                if sub_cls
                else 0.0
            )
            trends_out.append(
                TrendEntry(
                    date=datetime.utcnow().strftime("%Y-%m"),
                    topic=sc.category,
                    count=sc.total_items,
                    avg_score=round(avg_score, 1),
                )
            )

        # Risk signals (basic heuristic)
        risk_signals: list[RiskSignal] = []
        for cl in clusters_out:
            if cl.impact_score >= 70 and cl.relevance == "alta":
                risk_signals.append(
                    RiskSignal(
                        type="high_impact_cluster",
                        description=f"Cluster '{cl.label}' con alto impacto ({cl.impact_score})",
                        severity="H",
                        related_clusters=[cl.cluster_id],
                    )
                )

        # Build meta
        categories = set(cl.category for cl in clusters_out)
        meta = TrendmapMeta(
            generated_at=datetime.utcnow().isoformat() + "Z",
            total_articles=len(articles_raw),
            total_papers=len(papers_raw),
            total_filtered=len(all_articles),
            total_clusters=len(clusters_out),
            total_categories=len(categories),
            silhouette_score=round(silhouette, 3),
        )

        response = TrendmapResponse(
            meta=meta,
            clusters=clusters_out,
            super_clusters=super_clusters_out,
            articles=articles_out,
            trends=trends_out,
            insights=[],
            recommendations=[],
            risk_signals=risk_signals,
        )

        # Write trendmap.json
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / "trendmap.json"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(response.model_dump_json(indent=2))
        logger.info(
            "Saved trendmap.json: %d clusters, %d articles",
            len(clusters_out), len(articles_out),
        )

        return response


__all__ = ["TrendmapPipeline"]
