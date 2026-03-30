"""CLI for historical analysis: clustering + Power BI export.

Takes an existing articles.jsonl and runs:
1. ClusterEngine — TF-IDF clustering, trend timelines, hype indicators
2. PowerBIExporter — JSON output for Power BI dashboards

Usage:
    python -m extractor.analyze --input out/articles.jsonl --out out/analysis
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .capabilities.clustering import ClusterEngine
from .capabilities.powerbi_export import PowerBIExporter, export_powerbi_json
from .utils import setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="extractor.analyze",
        description="Run historical analysis (clustering + Power BI export) on articles",
    )
    parser.add_argument("--input", required=True, nargs="+", help="Path(s) to articles.jsonl — multiple files are merged with source tags")
    parser.add_argument("--out", default="out/analysis", help="Output directory")
    parser.add_argument("--min-score", type=int, default=40, help="Min relevance_score to include (default: 40)")
    parser.add_argument(
        "--analyzer",
        choices=["llm", "tfidf"],
        default="llm",
        help="Analysis method: llm (Bedrock, falls back to tfidf) or tfidf only",
    )
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def load_articles(path: str, min_score: int = 0, source_tag: str = "") -> list[dict]:
    """Load articles from JSONL, optionally filtering by min score."""
    articles = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            doc = json.loads(line)
            score = doc.get("relevance_score") or 0
            if score >= min_score:
                if source_tag:
                    doc["_source_file"] = source_tag
                articles.append(doc)
    return articles


def _export_llm_as_powerbi(
    llm_analysis: dict,
    items: list[dict],
    out_dir: Path,
    logger: Any,
) -> None:
    """Convert LLM analysis JSON to Power BI compatible format."""
    from datetime import datetime, timezone

    clusters_pbi = []
    for cl in llm_analysis.get("clusters", []):
        cluster_items = []
        for idx in cl.get("article_indices", []):
            if 0 <= idx < len(items):
                cluster_items.append(items[idx])
        clusters_pbi.append({
            "cluster_id": cl.get("id", ""),
            "label": cl.get("label", ""),
            "centroid_keywords": cl.get("keywords", [])[:4],
            "item_count": cl.get("item_count", len(cluster_items)),
            "items": cluster_items,
        })

    trends_pbi = []
    for t in llm_analysis.get("trends", []):
        trends_pbi.append({
            "date": datetime.now(timezone.utc).strftime("%Y-%m"),
            "topic": t.get("trend", ""),
            "count": 0,
            "avg_score": t.get("momentum", 0) * 100,
        })

    hype_pbi = []
    for t in llm_analysis.get("trends", []):
        hype_pbi.append({
            "topic": t.get("trend", ""),
            "momentum": t.get("momentum", 0),
            "maturity_stage": t.get("maturity_stage", ""),
        })

    top_items = sorted(items, key=lambda x: x.get("relevance_score", 0), reverse=True)[:20]
    top_pbi = [
        {
            "title": it.get("title", ""),
            "url": it.get("url", ""),
            "mode": it.get("mode", ""),
            "score": it.get("relevance_score", 0),
            "cluster_id": "",
        }
        for it in top_items
    ]

    powerbi = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "period": "analysis",
            "modes": ["historical"],
            "analyzer": "llm",
        },
        "clusters": clusters_pbi,
        "trend_timeline": trends_pbi,
        "hype_indicators": hype_pbi,
        "top_items": top_pbi,
        "key_insights": llm_analysis.get("key_insights", []),
        "recommendations": llm_analysis.get("recommendations", []),
        "risk_signals": llm_analysis.get("risk_signals", []),
    }

    pbi_path = out_dir / "powerbi_data.json"
    with open(pbi_path, "w", encoding="utf-8") as f:
        json.dump(powerbi, f, indent=2, ensure_ascii=False)
    logger.info("Power BI JSON (from LLM) saved to: %s", pbi_path)


def main():
    args = parse_args()
    logger = setup_logging(debug=args.debug)

    # Load articles from one or more files
    articles = []
    for input_path_str in args.input:
        input_path = Path(input_path_str)
        if not input_path.exists():
            logger.error("Input file not found: %s", input_path)
            return 1
        tag = input_path.stem  # e.g. "articles" or "articles_papers"
        loaded = load_articles(str(input_path), min_score=args.min_score, source_tag=tag)
        logger.info("Loaded %d articles from %s (min_score=%d)", len(loaded), input_path.name, args.min_score)
        articles.extend(loaded)

    logger.info("Total: %d articles from %d file(s)", len(articles), len(args.input))

    if len(articles) < 3:
        logger.warning("Too few articles for clustering (need at least 3)")
        return 1

    # Prepare items for clustering: need title + excerpt + published_at + score
    items = []
    for doc in articles:
        items.append({
            "title": doc.get("title", ""),
            "excerpt": doc.get("excerpt", "") or doc.get("text", "")[:500],
            "published_at": doc.get("published_at", ""),
            "relevance_score": doc.get("relevance_score", 0),
            "source_id": doc.get("source_id", ""),
            "url": doc.get("url", ""),
            "category": doc.get("category") or doc.get("risk_type") or "",
            "severity": doc.get("severity", ""),
            "mode": doc.get("query_type") or doc.get("origin", ""),
        })

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Try LLM analysis first ──
    llm_analysis = None
    if args.analyzer == "llm":
        logger.info("Running LLM analysis on %d articles...", len(items))
        from .capabilities.llm_analyze import LLMAnalyzer

        analyzer = LLMAnalyzer()
        llm_analysis = analyzer.analyze(articles, focus="vigilancia tecnológica")

        if llm_analysis:
            logger.info("LLM analysis complete")

            # Save LLM analysis
            llm_path = out_dir / "llm_analysis.json"
            with open(llm_path, "w", encoding="utf-8") as f:
                json.dump(llm_analysis, f, indent=2, ensure_ascii=False)
            logger.info("LLM analysis saved to: %s", llm_path)

            # Convert LLM analysis to Power BI format
            _export_llm_as_powerbi(llm_analysis, items, out_dir, logger)

            # Print summary
            clusters = llm_analysis.get("clusters", [])
            logger.info("LLM found %d clusters:", len(clusters))
            for cl in clusters:
                logger.info(
                    "  [%s] %s (%d items) — %s",
                    cl.get("id"), cl.get("label"), cl.get("item_count", 0),
                    cl.get("relevance", ""),
                )

            trends = llm_analysis.get("trends", [])
            logger.info("Trends: %d", len(trends))
            for t in trends:
                logger.info(
                    "  %s — %s (momentum=%.1f, stage=%s)",
                    t.get("trend"), t.get("direction"),
                    t.get("momentum", 0), t.get("maturity_stage"),
                )

            insights = llm_analysis.get("key_insights", [])
            for ins in insights:
                logger.info("  Insight: %s", ins)
        else:
            logger.warning("LLM analysis failed — falling back to TF-IDF")

    # ── TF-IDF clustering (fallback or explicit) ──
    if not llm_analysis or args.analyzer == "tfidf":
        logger.info("Running TF-IDF ClusterEngine on %d items...", len(items))
        engine = ClusterEngine()
        clustering_output = engine.cluster(items)

        logger.info(
            "Clustering complete: %d clusters, %d trend entries, %d hype indicators",
            len(clustering_output.clusters),
            len(clustering_output.trend_timeline),
            len(clustering_output.hype_indicators),
        )

        for cl in clustering_output.clusters:
            logger.info(
                "  Cluster '%s': %d items, keywords=%s",
                cl.label, cl.item_count, cl.centroid_keywords,
            )

        # Power BI export
        logger.info("Exporting Power BI JSON...")
        powerbi_path = export_powerbi_json(
            clustering_output=clustering_output,
            out_dir=str(out_dir),
            period="analysis",
            modes=["historical"],
        )
        logger.info("Power BI JSON saved to: %s", powerbi_path)

        # Save cluster summary
        summary = {
            "total_articles": len(articles),
            "total_clusters": len(clustering_output.clusters),
            "clusters": [
                {
                    "id": cl.cluster_id,
                    "label": cl.label,
                    "keywords": cl.centroid_keywords,
                    "item_count": cl.item_count,
                    "sample_titles": [
                        it.get("title", "")[:80] for it in cl.items[:3]
                    ],
                }
                for cl in clustering_output.clusters
            ],
            "trend_timeline": [
                {
                    "date": t.date,
                    "topic": t.topic,
                    "count": t.count,
                    "avg_score": round(t.avg_score, 1),
                }
                for t in clustering_output.trend_timeline
            ],
            "hype_indicators": [
                {
                    "topic": h.topic,
                    "momentum": round(h.momentum, 2),
                    "maturity_stage": h.maturity_stage,
                }
                for h in clustering_output.hype_indicators
            ],
        }

        summary_path = out_dir / "cluster_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        logger.info("Cluster summary saved to: %s", summary_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
