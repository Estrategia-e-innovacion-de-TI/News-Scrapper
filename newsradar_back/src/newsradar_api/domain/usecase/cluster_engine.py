"""ClusterEngine — TF-IDF based thematic clustering.

Groups items by thematic similarity using TF-IDF + cosine similarity.
Computes trend_timeline and hype_indicators for historical analysis.

Ported from news_radar_mvp/extractor/capabilities/clustering.py
Validates: Requirements 13.1-13.6
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Spanish stop words (supplement sklearn's built-in English set)
# ---------------------------------------------------------------------------

SPANISH_STOP_WORDS = frozenset({
    "de", "la", "el", "en", "y", "los", "del", "las", "un", "por", "con",
    "una", "su", "para", "es", "al", "lo", "como", "más", "pero", "sus",
    "le", "ya", "o", "fue", "este", "ha", "si", "porque", "esta", "son",
    "entre", "está", "cuando", "muy", "sin", "sobre", "ser", "también",
    "me", "hasta", "hay", "donde", "han", "quien", "están", "estado",
    "desde", "todo", "nos", "durante", "todos", "uno", "les", "ni",
    "contra", "otros", "ese", "eso", "ante", "ellos", "e", "esto", "mí",
    "antes", "algunos", "qué", "unos", "yo", "otro", "otras", "otra",
    "él", "tanto", "esa", "estos", "mucho", "quienes", "nada", "muchos",
    "cual", "poco", "ella", "estar", "estas", "algunas", "algo", "nosotros",
    "mi", "mis", "tú", "te", "ti", "tu", "tus", "ellas", "nosotras",
    "vosotros", "vosotras", "os", "mío", "mía", "míos", "mías", "tuyo",
    "tuya", "tuyos", "tuyas", "suyo", "suya", "suyos", "suyas", "nuestro",
    "nuestra", "nuestros", "nuestras", "vuestro", "vuestra", "vuestros",
    "vuestras", "esos", "esas", "estoy", "estás", "está", "estamos",
    "estáis", "están", "esté", "estés", "estemos", "estéis", "estén",
    "estaré", "estarás", "estará", "estaremos", "estaréis", "estarán",
    "estaría", "estarías", "estaríamos", "estaríais", "estarían", "estaba",
    "estabas", "estábamos", "estabais", "estaban", "estuve", "estuviste",
    "estuvo", "estuvimos", "estuvisteis", "estuvieron", "estuviera",
    "estuvieras", "estuviéramos", "estuvierais", "estuvieran", "estuviese",
    "estuvieses", "estuviésemos", "estuvieseis", "estuviesen", "estando",
    "que", "se", "no",
})

# Valid Gartner hype cycle stages
VALID_MATURITY_STAGES = frozenset({
    "innovation_trigger",
    "peak_of_inflated_expectations",
    "trough_of_disillusionment",
    "slope_of_enlightenment",
    "plateau_of_productivity",
})


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ClusterResult:
    """A single cluster of thematically similar items."""

    cluster_id: str
    label: str
    centroid_keywords: list[str]  # top 4
    item_count: int
    items: list[dict[str, Any]]  # [{title, url, mode, score, published_at}]


@dataclass
class TrendEntry:
    """Count and average score for a topic in a given month."""

    date: str  # YYYY-MM
    topic: str
    count: int
    avg_score: float


@dataclass
class HypeIndicator:
    """Momentum and maturity stage for a topic."""

    topic: str
    momentum: float  # 0.0–1.0
    maturity_stage: str  # one of 5 Gartner stages


@dataclass
class ClusteringOutput:
    """Full output of the clustering engine."""

    clusters: list[ClusterResult]
    trend_timeline: list[TrendEntry]
    hype_indicators: list[HypeIndicator]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_text(item: dict[str, Any]) -> str:
    """Build the text corpus entry from an item's title + excerpt."""
    title = item.get("title", "") or ""
    excerpt = item.get("excerpt") or item.get("text") or ""
    return f"{title} {excerpt}".strip()


def _get_score(item: dict[str, Any]) -> float:
    """Extract a numeric score from an item."""
    return float(item.get("score") or item.get("relevance_score") or 0)


def _get_published_month(item: dict[str, Any]) -> str | None:
    """Extract YYYY-MM from published_at."""
    pub = item.get("published_at")
    if not pub:
        return None
    try:
        if isinstance(pub, str):
            dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
        elif isinstance(pub, datetime):
            dt = pub
        else:
            return None
        return dt.strftime("%Y-%m")
    except (ValueError, TypeError):
        return None


def _item_to_dict(item: dict[str, Any]) -> dict[str, Any]:
    """Normalise an item to the output dict format."""
    return {
        "title": item.get("title", ""),
        "url": item.get("url", ""),
        "mode": item.get("mode", ""),
        "score": _get_score(item),
        "published_at": item.get("published_at", ""),
    }


# ---------------------------------------------------------------------------
# Trend timeline computation
# ---------------------------------------------------------------------------

def _compute_trend_timeline(
    clusters: list[ClusterResult],
) -> list[TrendEntry]:
    """Compute count and avg_score per topic per month."""
    buckets: dict[tuple[str, str], list[float]] = defaultdict(list)

    for cluster in clusters:
        topic = cluster.label
        for item in cluster.items:
            month = _get_published_month(item)
            if month is None:
                continue
            buckets[(month, topic)].append(item.get("score", 0) or 0)

    entries: list[TrendEntry] = []
    for (month, topic) in sorted(buckets.keys()):
        score_list = buckets[(month, topic)]
        entries.append(TrendEntry(
            date=month,
            topic=topic,
            count=len(score_list),
            avg_score=round(sum(score_list) / len(score_list), 2) if score_list else 0.0,
        ))
    return entries


# ---------------------------------------------------------------------------
# Hype indicators computation
# ---------------------------------------------------------------------------

def _compute_hype_indicators(
    clusters: list[ClusterResult],
    trend_timeline: list[TrendEntry],
) -> list[HypeIndicator]:
    """Compute momentum and maturity_stage per topic.

    Momentum = rate of change in mentions over the last 3 months (0.0-1.0).
    Maturity stage = heuristic based on momentum + total count.
    """
    topic_months: dict[str, dict[str, int]] = defaultdict(dict)
    for entry in trend_timeline:
        topic_months[entry.topic][entry.date] = entry.count

    all_months = sorted({e.date for e in trend_timeline})

    indicators: list[HypeIndicator] = []
    for cluster in clusters:
        topic = cluster.label
        months_data = topic_months.get(topic, {})
        total_count = cluster.item_count

        momentum = _calculate_momentum(months_data, all_months)
        stage = _determine_maturity_stage(momentum, total_count)

        indicators.append(HypeIndicator(
            topic=topic,
            momentum=momentum,
            maturity_stage=stage,
        ))

    return indicators


def _calculate_momentum(
    months_data: dict[str, int],
    all_months: list[str],
) -> float:
    """Calculate momentum as rate of change over last 3 months.

    Returns a float in [0.0, 1.0].
    """
    if len(all_months) < 2:
        return 0.5  # neutral if insufficient data

    recent = all_months[-3:] if len(all_months) >= 3 else all_months
    counts = [months_data.get(m, 0) for m in recent]

    if len(counts) < 2:
        return 0.5

    first = counts[0]
    last = counts[-1]

    if first == 0 and last == 0:
        return 0.0
    if first == 0:
        return 1.0  # new topic appearing

    change_ratio = (last - first) / max(first, 1)
    momentum = max(0.0, min(1.0, 0.5 + change_ratio * 0.25))
    return round(momentum, 2)


def _determine_maturity_stage(momentum: float, total_count: int) -> str:
    """Heuristic mapping of momentum + total_count to Gartner stage."""
    if total_count <= 2:
        return "innovation_trigger"
    if momentum >= 0.7:
        return "peak_of_inflated_expectations"
    if momentum <= 0.2:
        return "trough_of_disillusionment"
    if momentum >= 0.4 and total_count >= 10:
        return "slope_of_enlightenment"
    if momentum >= 0.3 and total_count >= 20:
        return "plateau_of_productivity"
    return "innovation_trigger"


# ---------------------------------------------------------------------------
# ClusterEngine
# ---------------------------------------------------------------------------

class ClusterEngine:
    """TF-IDF based thematic clustering engine.

    Validates: Requirements 13.1-13.6

    Parameters
    ----------
    similarity_threshold : float
        Minimum cosine similarity for items to be in the same cluster (default 0.3).
    min_cluster_size : int
        Minimum items per cluster; smaller clusters get merged (default 3).
    min_items_for_clustering : int
        Below this count, skip clustering entirely (default 6).
    """

    def __init__(
        self,
        similarity_threshold: float = 0.3,
        min_cluster_size: int = 3,
        min_items_for_clustering: int = 6,
        outlier_std_threshold: float = 2.0,
    ) -> None:
        self.similarity_threshold = similarity_threshold
        self.min_cluster_size = min_cluster_size
        self.min_items_for_clustering = min_items_for_clustering
        self.outlier_std_threshold = outlier_std_threshold

    def cluster(self, items: list[dict[str, Any]]) -> ClusteringOutput:
        """Cluster a list of items and compute trends + hype indicators.

        Parameters
        ----------
        items
            List of dicts, each with at least ``title``, ``excerpt``/``text``,
            ``url``, ``score``/``relevance_score``, ``published_at``.

        Returns
        -------
        ClusteringOutput
        """
        if not items:
            return ClusteringOutput(clusters=[], trend_timeline=[], hype_indicators=[])

        # Req 13.2: <6 items → single "all_items" cluster, skip TF-IDF
        if len(items) < self.min_items_for_clustering:
            return self._single_cluster(items)

        # Req 13.6: fallback to single cluster if sklearn fails
        try:
            return self._sklearn_cluster(items)
        except Exception:
            logger.error(
                "Clustering failed — returning all items as single cluster",
                exc_info=True,
            )
            return self._single_cluster(items)

    # ------------------------------------------------------------------
    # Single-cluster fallback
    # ------------------------------------------------------------------

    def _single_cluster(self, items: list[dict[str, Any]]) -> ClusteringOutput:
        """Return all items in a single 'all_items' cluster."""
        item_dicts = [_item_to_dict(it) for it in items]
        cluster = ClusterResult(
            cluster_id="all_items",
            label="all_items",
            centroid_keywords=[],
            item_count=len(items),
            items=item_dicts,
        )
        timeline = _compute_trend_timeline([cluster])
        hype = _compute_hype_indicators([cluster], timeline)
        return ClusteringOutput(
            clusters=[cluster],
            trend_timeline=timeline,
            hype_indicators=hype,
        )

    # ------------------------------------------------------------------
    # sklearn-based clustering
    # ------------------------------------------------------------------

    def _sklearn_cluster(self, items: list[dict[str, Any]]) -> ClusteringOutput:
        """Perform TF-IDF + agglomerative clustering.

        Validates: Requirements 13.1, 13.3, 13.4, 13.5
        """
        from sklearn.cluster import AgglomerativeClustering
        from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        # 1. Build corpus
        corpus = [_get_text(it) for it in items]

        # Req 13.1: TF-IDF with max_features=5000, stop words en+es
        combined_stop_words = list(ENGLISH_STOP_WORDS | SPANISH_STOP_WORDS)
        vectorizer = TfidfVectorizer(
            stop_words=combined_stop_words,
            max_features=5000,
            min_df=1,
        )
        tfidf_matrix = vectorizer.fit_transform(corpus)

        # If vocabulary is empty, fall back to single cluster
        if tfidf_matrix.shape[1] == 0:
            return self._single_cluster(items)

        # 2. Req 13.1: AgglomerativeClustering with distance_threshold
        distance_threshold = 1.0 - self.similarity_threshold  # 0.7
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=distance_threshold,
            metric="cosine",
            linkage="average",
        )
        labels = clustering.fit_predict(tfidf_matrix.toarray())

        # 3. Group items by cluster label
        cluster_groups: dict[int, list[int]] = defaultdict(list)
        for idx, lbl in enumerate(labels):
            cluster_groups[int(lbl)].append(idx)

        # 4. Req 13.3: Merge small clusters (<min_cluster_size) into nearest
        cluster_groups = self._merge_small_clusters(
            cluster_groups, tfidf_matrix, items,
        )

        # 4.1: Move centroid-distance outliers to "unclustered" to reduce noisy assignments.
        cluster_groups = self._reassign_far_outliers(cluster_groups, tfidf_matrix)

        # 5. Build ClusterResult objects
        feature_names = vectorizer.get_feature_names_out()
        clusters: list[ClusterResult] = []

        for cluster_label, indices in sorted(cluster_groups.items()):
            cluster_items = [_item_to_dict(items[i]) for i in indices]

            # Req 13.4: top 4 keywords from centroid TF-IDF
            cluster_vectors = tfidf_matrix[indices]
            centroid = np.asarray(cluster_vectors.mean(axis=0)).flatten()
            top_indices = centroid.argsort()[-4:][::-1]
            keywords = [
                str(feature_names[i]) for i in top_indices if centroid[i] > 0
            ]
            keywords = keywords[:4]

            label_str = (
                " ".join(keywords) if keywords else f"cluster_{cluster_label}"
            )
            cid = (
                f"cluster_{cluster_label}" if cluster_label >= 0 else "unclustered"
            )

            clusters.append(ClusterResult(
                cluster_id=cid,
                label=label_str,
                centroid_keywords=keywords,
                item_count=len(indices),
                items=cluster_items,
            ))

        # 6. Req 13.5: trend_timeline and hype_indicators
        timeline = _compute_trend_timeline(clusters)
        hype = _compute_hype_indicators(clusters, timeline)

        return ClusteringOutput(
            clusters=clusters,
            trend_timeline=timeline,
            hype_indicators=hype,
        )

    def _reassign_far_outliers(
        self,
        cluster_groups: dict[int, list[int]],
        tfidf_matrix: Any,
    ) -> dict[int, list[int]]:
        """Move items with distance > mean + N*std to unclustered.

        This keeps clusters tighter and prevents weakly related items from
        inflating noise in silhouette-like separation metrics.
        """
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity

        if self.outlier_std_threshold <= 0:
            return cluster_groups

        result: dict[int, list[int]] = {}
        unclustered_indices: list[int] = list(cluster_groups.get(-1, []))

        for lbl, indices in cluster_groups.items():
            if lbl == -1:
                continue

            # Keep tiny clusters untouched; they are already handled by merge logic.
            if len(indices) < max(3, self.min_cluster_size):
                result[lbl] = list(indices)
                continue

            vectors = tfidf_matrix[indices]
            centroid = np.asarray(vectors.mean(axis=0)).flatten().reshape(1, -1)
            similarities = cosine_similarity(vectors, centroid).reshape(-1)
            distances = 1.0 - similarities

            mean_distance = float(np.mean(distances))
            std_distance = float(np.std(distances))
            threshold = mean_distance + self.outlier_std_threshold * std_distance

            kept: list[int] = []
            for local_idx, global_idx in enumerate(indices):
                if float(distances[local_idx]) > threshold:
                    unclustered_indices.append(global_idx)
                else:
                    kept.append(global_idx)

            if kept:
                result[lbl] = kept

        if unclustered_indices:
            result[-1] = unclustered_indices

        return result

    def _merge_small_clusters(
        self,
        cluster_groups: dict[int, list[int]],
        tfidf_matrix: Any,
        items: list[dict[str, Any]],
    ) -> dict[int, list[int]]:
        """Merge clusters with <min_cluster_size items into nearest or unclustered.

        Validates: Requirement 13.3
        """
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity

        small: list[int] = []
        large: list[int] = []

        for lbl, indices in cluster_groups.items():
            if len(indices) < self.min_cluster_size:
                small.append(lbl)
            else:
                large.append(lbl)

        if not small:
            return cluster_groups

        # If no large clusters exist, merge everything to unclustered
        if not large:
            merged: dict[int, list[int]] = {}
            all_indices: list[int] = []
            for lbl in small:
                all_indices.extend(cluster_groups[lbl])
            merged[-1] = all_indices
            return merged

        # Compute centroids for large clusters
        large_centroids: dict[int, Any] = {}
        for lbl in large:
            indices = cluster_groups[lbl]
            vectors = tfidf_matrix[indices]
            large_centroids[lbl] = np.asarray(vectors.mean(axis=0)).flatten()

        # For each small cluster, find nearest large cluster by cosine
        result = {lbl: list(cluster_groups[lbl]) for lbl in large}
        for small_lbl in small:
            small_indices = cluster_groups[small_lbl]
            small_vectors = tfidf_matrix[small_indices]
            small_centroid = np.asarray(small_vectors.mean(axis=0)).flatten()

            best_lbl = large[0]
            best_sim = -1.0
            for lbl in large:
                sim = cosine_similarity(
                    small_centroid.reshape(1, -1),
                    large_centroids[lbl].reshape(1, -1),
                )[0][0]
                if sim > best_sim:
                    best_sim = sim
                    best_lbl = lbl

            if best_sim >= self.similarity_threshold:
                result[best_lbl].extend(small_indices)
            else:
                # Assign to unclustered
                if -1 not in result:
                    result[-1] = []
                result[-1].extend(small_indices)

        return result


__all__ = [
    "ClusterEngine",
    "ClusterResult",
    "ClusteringOutput",
    "TrendEntry",
    "HypeIndicator",
    "SPANISH_STOP_WORDS",
    "VALID_MATURITY_STAGES",
]
