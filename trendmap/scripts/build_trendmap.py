"""Pasos 2-5 — Build the complete trendmap.json dataset.

Loads articles + clusters, computes embeddings (Bedrock), UMAP projection,
hulls, impact/horizon scores, and writes data/trendmap.json.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────

def _sha256(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()[:16]


def _parse_date(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _load_jsonl(path: Path, min_year: int = 2024, min_score: int = 55) -> list[dict]:
    """Load JSONL, filtering old items, low-relevance, and off-topic items."""
    _OFF_TOPIC = {
        "yolo", "3d city", "occupancy", "robot manipulation", "drone target",
        "soap opera", "lululemon", "biodesign", "humanoid robot", "kid-size",
        "window-washing", "emergency vehicle", "rocket turbine", "space power",
        "child safety", "creator revenue", "joint ev project", "robotaxi",
        "optical clock", "dirac operator", "cosmic coincidence", "wine-glass",
        "dark energy", "black hole", "brickwork circuit", "biological membrane",
        "hall viscosity", "cpt violation", "baryon asymmetry", "majorana",
        "tensor-network fourier", "perturbations of", "electromechanical",
        "uav-detr", "anti-drone", "abot-phys",
    }
    items = []
    if not path.exists():
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


# ── Embedding cache ──────────────────────────────────────────────────

class EmbeddingCache:
    def __init__(self, path: Path):
        self.path = path
        self.cache: dict[str, list[float]] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            with open(self.path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        self.cache[entry["hash"]] = entry["embedding"]
            logger.info("Loaded %d cached embeddings", len(self.cache))

    def get(self, text_hash: str) -> list[float] | None:
        return self.cache.get(text_hash)

    def put(self, text_hash: str, embedding: list[float]):
        self.cache[text_hash] = embedding
        with open(self.path, "a") as f:
            f.write(json.dumps({"hash": text_hash, "embedding": embedding}) + "\n")


# ── Bedrock embeddings ───────────────────────────────────────────────

def embed_texts_bedrock(
    texts: list[str],
    model_id: str,
    region: str,
    cache: EmbeddingCache,
    max_len: int = 2000,
    batch_size: int = 25,
) -> list[list[float]]:
    """Embed texts using Amazon Bedrock. Uses cache to avoid re-computation."""
    import boto3

    client = boto3.client("bedrock-runtime", region_name=region, verify=False)
    results: list[list[float] | None] = [None] * len(texts)
    to_embed: list[tuple[int, str, str]] = []  # (index, hash, text)

    for i, text in enumerate(texts):
        truncated = text[:max_len]
        h = _sha256(truncated)
        cached = cache.get(h)
        if cached is not None:
            results[i] = cached
        else:
            to_embed.append((i, h, truncated))

    logger.info("Embeddings: %d cached, %d to compute", len(texts) - len(to_embed), len(to_embed))

    for batch_start in range(0, len(to_embed), batch_size):
        batch = to_embed[batch_start:batch_start + batch_size]
        for idx, h, text in batch:
            try:
                body = json.dumps({"inputText": text})
                resp = client.invoke_model(
                    modelId=model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=body,
                )
                result = json.loads(resp["body"].read())
                emb = result.get("embedding", [])
                results[idx] = emb
                cache.put(h, emb)
            except Exception as exc:
                logger.warning("Embedding failed for text[:50]=%s: %s", text[:50], exc)
                results[idx] = []
            time.sleep(0.1)  # rate limit

        if batch_start > 0 and batch_start % 100 == 0:
            logger.info("Embedded %d/%d", batch_start, len(to_embed))

    return [r if r is not None else [] for r in results]


# ── Fallback: TF-IDF embeddings ──────────────────────────────────────

def embed_texts_tfidf(texts: list[str]) -> list[list[float]]:
    """Fallback: use TF-IDF vectors as pseudo-embeddings."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    vectorizer = TfidfVectorizer(max_features=256, stop_words="english")
    matrix = vectorizer.fit_transform(texts)
    return matrix.toarray().tolist()


# ── UMAP projection ─────────────────────────────────────────────────

def project_umap(
    embeddings: list[list[float]],
    n_neighbors: int = 10,
    min_dist: float = 0.3,
    random_state: int = 42,
    spread: float = 2.0,
) -> list[tuple[float, float]]:
    """Project embeddings to 2D using UMAP."""
    import umap

    valid_mask = np.array([len(e) > 0 for e in embeddings])
    if valid_mask.sum() < 3:
        return [(0.0, 0.0)] * len(embeddings)

    max_dim = max(len(e) for e in embeddings if len(e) > 0)
    padded = np.zeros((len(embeddings), max_dim))
    for i, e in enumerate(embeddings):
        if len(e) > 0:
            padded[i, :len(e)] = e

    effective_neighbors = min(n_neighbors, valid_mask.sum() - 1)
    if effective_neighbors < 2:
        effective_neighbors = 2

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


# ── Hull computation ─────────────────────────────────────────────────

def compute_hull(points: list[tuple[float, float]], config: dict) -> list[list[float]]:
    """Compute hull polygon, trimming outlier points for tighter shapes."""
    if len(points) < 2:
        if len(points) == 1:
            x, y = points[0]
            r = config.get("circle_radius_factor", 0.05)
            return [[x + r * math.cos(a), y + r * math.sin(a)]
                    for a in np.linspace(0, 2 * math.pi, 16)]
        return []

    if len(points) < config.get("min_points_convex", 3):
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
        r = config.get("circle_radius_factor", 0.05) * 2
        return [[cx + r * math.cos(a), cy + r * math.sin(a)]
                for a in np.linspace(0, 2 * math.pi, 16)]

    # Trim to 85th percentile closest to centroid for tighter hulls
    pts = np.array(points)
    centroid = pts.mean(axis=0)
    dists = np.linalg.norm(pts - centroid, axis=1)
    if len(pts) > 5:
        threshold = np.percentile(dists, 85)
        pts = pts[dists <= threshold]

    if len(pts) < 3:
        pts = np.array(points)  # fallback to all

    from scipy.spatial import ConvexHull
    try:
        hull = ConvexHull(pts)
        return [[float(pts[v, 0]), float(pts[v, 1])] for v in hull.vertices]
    except Exception:
        return []


# ── Impact & Horizon scores ─────────────────────────────────────────

def compute_impact(cluster: dict, articles: list[dict], config: dict) -> float:
    """Compute impact score (0-100) for a cluster."""
    weights = config.get("impact", {})
    w_score = weights.get("weight_score", 0.45)
    w_volume = weights.get("weight_volume", 0.25)
    w_recency = weights.get("weight_recency", 0.20)
    w_signals = weights.get("weight_signals", 0.10)

    scores = [a.get("relevance_score", 0) for a in articles]
    avg_score = np.mean(scores) if scores else 0

    # Volume: normalize by log
    volume = min(math.log1p(len(articles)) / math.log1p(100), 1.0) * 100

    # Recency: median days since publish
    now = datetime.utcnow()
    days = []
    for a in articles:
        d = _parse_date(a.get("published_at"))
        if d:
            days.append((now - d.replace(tzinfo=None)).days)
    median_days = np.median(days) if days else 30
    recency = max(0, 100 - median_days * 3)  # decay: 0 at ~33 days

    signals = 10 if cluster.get("relevance") == "alta" else 5

    impact = w_score * avg_score + w_volume * volume + w_recency * recency + w_signals * signals
    return round(min(max(impact, 0), 100), 1)


def compute_horizon(cluster: dict, config: dict) -> float:
    """Compute horizon/maturity score (0-1) for a cluster.
    
    Uses maturity_stage if available, otherwise estimates from
    impact and volume heuristics.
    """
    horizon_map = config.get("horizon", {})
    stage = cluster.get("maturity_stage", "")
    if stage in horizon_map:
        return horizon_map[stage]

    # Heuristic based on impact and item count
    impact = cluster.get("impact_score", 50)
    items = cluster.get("item_count", 0)
    relevance = cluster.get("relevance", "media")

    # More items + higher impact = more mature
    volume_signal = min(items / 30, 1.0)  # saturates at 30 items
    impact_signal = impact / 100.0

    if impact_signal >= 0.7 and volume_signal >= 0.5:
        return 0.7  # slope of enlightenment
    elif impact_signal >= 0.6:
        return 0.3  # peak of expectations
    elif volume_signal >= 0.3:
        return 0.5  # trough
    elif impact_signal >= 0.4:
        return 0.1  # innovation trigger
    else:
        return 0.2


def _label_cluster_with_llm(titles: list[str]) -> tuple[str, str, list[str], str]:
    """Use LLM to generate label, summary, keywords, relevance for a cluster.
    
    Returns (label, summary, keywords, relevance).
    """
    from collections import Counter
    all_words = []
    for t in titles:
        all_words.extend(w.lower() for w in t.split() if len(w) >= 4)
    common = [w for w, _ in Counter(all_words).most_common(5)]
    fallback_label = " / ".join(common[:3]) if common else "Cluster"
    fallback_kws = common[:5]

    try:
        import boto3
        client = boto3.client("bedrock-runtime", region_name="us-east-1", verify=False)
        titles_text = "\n".join(f"- {t}" for t in titles[:20])
        prompt = f"""You are a tech trend analyst. Given these article titles from a semantic cluster,
generate a precise categorization.

Titles:
{titles_text}

Respond ONLY with this JSON:
{{
  "label": "<descriptive name, 3-6 words, in Spanish>",
  "category": "<one of: Ciberseguridad|Inteligencia Artificial|Blockchain/Cripto|Fintech/Banca Digital|Cloud/Datos|Regulación|Computación Cuántica|Innovación General>",
  "summary": "<1-2 sentence summary of the cluster theme, in Spanish>",
  "keywords": ["kw1","kw2","kw3","kw4","kw5"],
  "relevance": "<alta|media|baja> for fintech/cybersecurity sector"
}}"""

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300, "temperature": 0.0,
            "messages": [{"role": "user", "content": prompt}],
        })
        resp = client.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            contentType="application/json", accept="application/json", body=body,
        )
        import re
        text = json.loads(resp["body"].read())["content"][0]["text"]
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            parsed = json.loads(m.group())
            label = parsed.get("label", fallback_label)
            category = parsed.get("category", "")
            if category:
                label = f"[{category}] {label}"
            return (
                label,
                parsed.get("summary", ""),
                parsed.get("keywords", fallback_kws),
                parsed.get("relevance", "media"),
            )
    except Exception as exc:
        logger.debug("LLM cluster labeling failed: %s", exc)

    return fallback_label, "", fallback_kws, "media"


# ── Main build ───────────────────────────────────────────────────────

def main():
    config_path = Path(__file__).parent.parent / "config" / "trendmap.yml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    base = Path(__file__).parent.parent.parent
    paths = config.get("paths", {})

    # ── 1. Load & filter data ──
    articles_raw = _load_jsonl(base / paths.get("articles", "out/articles.jsonl"))
    papers_raw = _load_jsonl(base / paths.get("papers", "out/articles_papers.jsonl"))
    for a in articles_raw:
        a["_source_type"] = "news"
    for a in papers_raw:
        a["_source_type"] = "paper"
    all_articles = articles_raw + papers_raw
    logger.info("Loaded %d news + %d papers = %d total", len(articles_raw), len(papers_raw), len(all_articles))

    if len(all_articles) < 5:
        logger.error("Too few articles (%d). Run the pipeline first.", len(all_articles))
        return 1

    for i, a in enumerate(all_articles):
        a["article_id"] = _sha256(a.get("url", "") or a.get("title", str(i)))

    # ── 2. Embeddings ──
    embed_config = config.get("embeddings", {})
    cache_path = base / embed_config.get("cache_file", "trendmap/data/embeddings_cache.jsonl")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache = EmbeddingCache(cache_path)

    texts = [
        a.get("title", "") + "\n\n" + (a.get("excerpt", "") or a.get("text", "")[:500])
        for a in all_articles
    ]
    try:
        embeddings = embed_texts_bedrock(
            texts,
            model_id=embed_config.get("model_id", "amazon.titan-embed-text-v2:0"),
            region=embed_config.get("region", "us-east-1"),
            cache=cache,
            max_len=embed_config.get("max_text_length", 2000),
        )
        logger.info("Bedrock embeddings computed")
    except Exception as exc:
        logger.warning("Bedrock failed (%s), using TF-IDF", exc)
        embeddings = embed_texts_tfidf(texts)

    # ── 3. UMAP projection ──
    umap_config = config.get("umap", {})
    coords = project_umap(
        embeddings,
        n_neighbors=umap_config.get("n_neighbors", 10),
        min_dist=umap_config.get("min_dist", 0.3),
        random_state=umap_config.get("random_state", 42),
        spread=umap_config.get("spread", 2.0),
    )
    for i, (x, y) in enumerate(coords):
        all_articles[i]["x_embed"] = round(x, 4)
        all_articles[i]["y_embed"] = round(y, 4)

    # ── 4. Cluster on embeddings (HDBSCAN) ──
    logger.info("Clustering %d articles on embeddings...", len(all_articles))
    emb_array = np.array([e if len(e) > 0 else [0.0] * (len(embeddings[0]) if embeddings[0] else 1) for e in embeddings])

    # PCA to reduce noise before clustering (high-dim embeddings have noisy dims)
    from sklearn.decomposition import PCA
    n_components_pca = min(50, emb_array.shape[1], emb_array.shape[0] - 1)
    logger.info("PCA: %d dims → %d dims", emb_array.shape[1], n_components_pca)
    emb_reduced = PCA(n_components=n_components_pca, random_state=42).fit_transform(emb_array)

    # ── Find optimal K using Silhouette Score ──
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    k_min = max(3, len(all_articles) // 60)
    k_max = min(12, len(all_articles) // 10)
    best_k, best_score = k_min, -1
    logger.info("Testing K=%d..%d for optimal clusters", k_min, k_max)

    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        trial_labels = km.fit_predict(emb_reduced)
        sil = silhouette_score(emb_reduced, trial_labels, sample_size=min(500, len(emb_reduced)))
        logger.info("  K=%d → silhouette=%.3f", k, sil)
        if sil > best_score:
            best_score = sil
            best_k = k

    logger.info("Optimal K=%d (silhouette=%.3f) — using as reference", best_k, best_score)

    # ── HDBSCAN: only well-defined clusters, rest = unclustered ──
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

    # Compute silhouette on clustered points only
    if n_found >= 2:
        mask = labels >= 0
        if mask.sum() > n_found:
            from sklearn.metrics import silhouette_score as sil_fn
            best_score = sil_fn(emb_reduced[mask], labels[mask])
    logger.info("HDBSCAN: %d clusters, %d noise, silhouette=%.3f", n_found, n_noise, best_score)
    best_k = n_found

    cluster_article_map: dict[str, list[dict]] = {}
    for i, label in enumerate(labels):
        cid = f"cluster_{label}" if label >= 0 else "unclustered"
        all_articles[i]["cluster_id"] = cid
        cluster_article_map.setdefault(cid, []).append(all_articles[i])

    outlier_count = n_noise
    for cid, arts in sorted(cluster_article_map.items()):
        if cid != "unclustered":
            logger.info("  %s: %d articles", cid, len(arts))

    # ── 5. Label clusters with LLM ──
    llm_path = base / paths.get("llm_analysis", "out/analysis_combined/llm_analysis.json")
    llm_data = {}
    if llm_path.exists():
        with open(llm_path) as f:
            llm_data = json.load(f)
    trends_raw = llm_data.get("trends", [])

    clusters_raw = []
    for cid, cl_articles in sorted(cluster_article_map.items()):
        if cid == "unclustered":
            continue
        titles = [a.get("title", "")[:80] for a in cl_articles[:20]]
        label, summary, keywords, relevance = _label_cluster_with_llm(titles)
        clusters_raw.append({
            "id": cid,
            "label": label,
            "keywords": keywords,
            "summary": summary,
            "relevance": relevance,
        })

    # ── 6. Compute hulls, impact, horizon ──
    hull_config = config.get("hull", {})
    clusters_out = []
    for cl in clusters_raw:
        cid = cl["id"]
        cl_articles = cluster_article_map.get(cid, [])
        cl_coords = [(a["x_embed"], a["y_embed"]) for a in cl_articles if "x_embed" in a]
        cx = float(np.mean([p[0] for p in cl_coords])) if cl_coords else 0.0
        cy = float(np.mean([p[1] for p in cl_coords])) if cl_coords else 0.0
        hull_poly = compute_hull(cl_coords, hull_config)
        impact = compute_impact(cl, cl_articles, config)
        cl["impact_score"] = impact
        cl["item_count"] = len(cl_articles)
        horizon = compute_horizon(cl, config)
        clusters_out.append({
            "cluster_id": cid,
            "label": cl.get("label", cid),
            "relevance": cl.get("relevance", "media"),
            "summary": cl.get("summary", ""),
            "keywords": cl.get("keywords", [])[:6],
            "item_count": len(cl_articles),
            "avg_score": round(float(np.mean([a.get("relevance_score", 0) for a in cl_articles])), 1) if cl_articles else 0,
            "x_embed": round(cx, 4),
            "y_embed": round(cy, 4),
            "hull_polygon": hull_poly,
            "impact_score": impact,
            "horizon_score": horizon,
        })

    # ── 6b. Extract category from label and build super-clusters ──
    import re as _re
    category_map: dict[str, list[dict]] = {}
    for cl in clusters_out:
        cat_match = _re.match(r"\[([^\]]+)\]", cl["label"])
        cat = cat_match.group(1) if cat_match else "Otros"
        cl["category"] = cat
        category_map.setdefault(cat, []).append(cl)

    # Build super-cluster hulls (union of all sub-cluster points)
    super_clusters = []
    for cat, sub_clusters in category_map.items():
        all_cat_articles = []
        for sc in sub_clusters:
            all_cat_articles.extend(cluster_article_map.get(sc["cluster_id"], []))
        cat_coords = [(a["x_embed"], a["y_embed"]) for a in all_cat_articles if "x_embed" in a]
        cat_hull = compute_hull(cat_coords, hull_config) if len(cat_coords) >= 3 else []
        cx = float(np.mean([p[0] for p in cat_coords])) if cat_coords else 0.0
        cy = float(np.mean([p[1] for p in cat_coords])) if cat_coords else 0.0
        super_clusters.append({
            "category": cat,
            "sub_cluster_ids": [sc["cluster_id"] for sc in sub_clusters],
            "item_count": len(all_cat_articles),
            "avg_score": round(float(np.mean([a.get("relevance_score", 0) for a in all_cat_articles])), 1) if all_cat_articles else 0,
            "x_embed": round(cx, 4),
            "y_embed": round(cy, 4),
            "hull_polygon": cat_hull,
        })
    logger.info("Super-clusters: %s", {sc["category"]: sc["item_count"] for sc in super_clusters})

    # ── 6c. Compute fresh hype cycle from cluster data ──
    # Momentum = normalized(avg_score * volume_factor * recency_factor)
    # Maturity = based on score distribution and volume
    trends_fresh = []
    for sc in super_clusters:
        cat = sc["category"]
        sub_cls = [c for c in clusters_out if c.get("category") == cat]
        total_items = sc["item_count"]
        avg_impact = float(np.mean([c["impact_score"] for c in sub_cls])) if sub_cls else 0

        # Momentum: 0-1 based on impact and volume
        volume_factor = min(total_items / 50, 1.0)
        momentum = round(min((avg_impact / 100) * 0.6 + volume_factor * 0.4, 1.0), 2)

        # Maturity stage heuristic:
        # High volume + high score = plateau/slope
        # High volume + medium score = peak
        # Low volume + high score = innovation trigger
        # Low volume + low score = trough
        if avg_impact >= 70 and volume_factor >= 0.5:
            stage = "slope_of_enlightenment"
        elif avg_impact >= 60:
            stage = "peak_of_inflated_expectations"
        elif volume_factor >= 0.3:
            stage = "trough_of_disillusionment"
        elif avg_impact >= 50:
            stage = "innovation_trigger"
        else:
            stage = "trough_of_disillusionment"

        trends_fresh.append({
            "trend": cat,
            "category": "tecnológica",
            "direction": "creciente" if momentum >= 0.5 else "estable" if momentum >= 0.3 else "decreciente",
            "momentum": momentum,
            "maturity_stage": stage,
            "description": f"{total_items} artículos, {len(sub_cls)} sub-clusters, impacto promedio {avg_impact:.0f}",
            "impact_on_finance": f"Impacto promedio: {avg_impact:.0f}/100",
        })

    # ── 7. Build output ──
    articles_out = [{
        "article_id": a.get("article_id", ""),
        "cluster_id": a.get("cluster_id", "unclustered"),
        "title": a.get("title", ""),
        "excerpt": (a.get("excerpt", "") or a.get("text", "")[:200])[:200],
        "url": a.get("url", ""),
        "published_at": a.get("published_at", ""),
        "relevance_score": a.get("relevance_score", 0),
        "source_id": a.get("source_id", ""),
        "source_type": a.get("_source_type", "unknown"),
        "x_embed": a.get("x_embed", 0),
        "y_embed": a.get("y_embed", 0),
    } for a in all_articles]

    stats_path = base / paths.get("output_dir", "trendmap/data") / "corpus_stats.json"
    corpus_stats = json.load(open(stats_path)) if stats_path.exists() else {}

    trendmap = {
        "meta": {
            "generated_at_utc": datetime.utcnow().isoformat() + "Z",
            "source_counts": {"news": len(articles_raw), "papers": len(papers_raw), "total": len(all_articles)},
            "date_range": {"min": corpus_stats.get("min_date"), "max": corpus_stats.get("max_date")},
            "config": {
                "umap": umap_config,
                "impact_weights": config.get("impact", {}),
                "embedding_model": embed_config.get("model_id", "tfidf-fallback"),
                "optimal_k": best_k,
                "outlier_threshold": "1 std dev from centroid",
                "silhouette_score": round(best_score, 3),
            },
            "methodology": {
                "embeddings": "Amazon Bedrock Titan Embed v2 (fallback: TF-IDF)",
                "clustering": f"KMeans (K={best_k}, optimal via Silhouette Score={best_score:.3f})",
                "outlier_removal": "Articles > 1 std dev from cluster centroid → unclustered",
                "labeling": "Claude Haiku via Bedrock (category + label + summary)",
                "momentum": "0.6 × (avg_impact/100) + 0.4 × min(volume/50, 1.0)",
                "maturity_stage": "Heuristic: impact ≥70 + volume ≥50% → slope; impact ≥60 → peak; volume ≥30% → trough; else → trigger",
                "impact_score": "45% avg_relevance_score + 25% log_volume + 20% recency_decay + 10% relevance_signal",
                "horizon_score": "Ordinal mapping: trigger=0.1, peak=0.3, trough=0.5, slope=0.7, plateau=0.9",
            },
        },
        "clusters": clusters_out,
        "super_clusters": super_clusters,
        "articles": articles_out,
        "trends": trends_fresh,
        "insights": llm_data.get("key_insights", []),
        "recommendations": llm_data.get("recommendations", []),
        "risk_signals": llm_data.get("risk_signals", []),
    }

    output_dir = base / paths.get("output_dir", "trendmap/data")
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "trendmap.json", "w", encoding="utf-8") as f:
        json.dump(trendmap, f, indent=2, ensure_ascii=False)

    logger.info("Saved trendmap.json: %d clusters, %d articles (%d unclustered)",
                len(clusters_out), len(articles_out),
                sum(1 for a in articles_out if a["cluster_id"] == "unclustered"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
