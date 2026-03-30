"""Generate an interactive HTML visualization of the analysis results.

Reads llm_analysis.json and/or powerbi_data.json and produces a single
self-contained HTML file with:
- Trend Map (radar/bubble chart by category and time horizon)
- Cluster visualization
- Hype cycle (Gartner stages)
- Key insights, recommendations, risk signals
- Top articles table

Usage:
    python visualize_analysis.py --input out/analysis_combined --out out/analysis_combined/dashboard.html
"""
from __future__ import annotations

import argparse
import json
import html as html_mod
import sys
from pathlib import Path


def load_json(path: Path) -> dict | None:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def build_html(llm: dict | None, pbi: dict | None) -> str:
    data = llm or pbi or {}
    clusters = data.get("clusters", [])
    trends = data.get("trends", [])
    insights = data.get("key_insights", [])
    recommendations = data.get("recommendations", [])
    risk_signals = data.get("risk_signals", [])
    top_items = (pbi or {}).get("top_items", [])
    hype = (pbi or {}).get("hype_indicators", []) or []

    # If trends come from LLM format
    if not hype and trends:
        hype = [
            {"topic": t.get("trend", ""), "momentum": t.get("momentum", 0),
             "maturity_stage": t.get("maturity_stage", "")}
            for t in trends
        ]

    # Build cluster cards HTML
    cluster_cards = ""
    for cl in clusters:
        label = html_mod.escape(cl.get("label", ""))
        kws = cl.get("keywords", cl.get("centroid_keywords", []))
        count = cl.get("item_count", 0)
        summary = html_mod.escape(cl.get("summary", ""))
        relevance = cl.get("relevance", "media")
        color = {"alta": "#2ecc71", "media": "#f39c12", "baja": "#e74c3c"}.get(relevance, "#95a5a6")
        kw_tags = "".join(f'<span class="tag">{html_mod.escape(k)}</span>' for k in kws[:5])
        cluster_cards += f"""
        <div class="card" style="border-left: 4px solid {color}">
            <h3>{label}</h3>
            <div class="meta">{count} artículos · Relevancia: <b style="color:{color}">{relevance}</b></div>
            <div class="tags">{kw_tags}</div>
            <p>{summary}</p>
        </div>"""

    # Build trend map HTML (inspired by Pivot's trend map)
    trend_rows = ""
    stage_labels = {
        "innovation_trigger": "🚀 Innovation Trigger",
        "peak_of_inflated_expectations": "📈 Peak of Expectations",
        "trough_of_disillusionment": "📉 Trough",
        "slope_of_enlightenment": "🔄 Slope of Enlightenment",
        "plateau_of_productivity": "✅ Plateau of Productivity",
    }
    for t in (trends or hype):
        name = html_mod.escape(t.get("trend", t.get("topic", "")))
        direction = t.get("direction", "")
        momentum = t.get("momentum", 0)
        stage = t.get("maturity_stage", "")
        stage_label = stage_labels.get(stage, stage)
        desc = html_mod.escape(t.get("description", ""))
        bar_width = int(momentum * 100)
        dir_icon = {"creciente": "↑", "estable": "→", "decreciente": "↓"}.get(direction, "•")
        trend_rows += f"""
        <tr>
            <td><b>{name}</b></td>
            <td>{dir_icon} {direction}</td>
            <td><div class="bar-bg"><div class="bar" style="width:{bar_width}%">{momentum:.1f}</div></div></td>
            <td>{stage_label}</td>
            <td class="desc">{desc}</td>
        </tr>"""

    # Build hype cycle SVG
    hype_svg = _build_hype_cycle_svg(hype)

    # Build insights/recommendations/risks
    insights_html = "".join(f"<li>{html_mod.escape(i)}</li>" for i in insights)
    recs_html = "".join(f"<li>{html_mod.escape(r)}</li>" for r in recommendations)
    risks_html = "".join(f"<li>⚠️ {html_mod.escape(r)}</li>" for r in risk_signals)

    # Build top items table
    top_rows = ""
    for i, item in enumerate(top_items[:20], 1):
        title = html_mod.escape(item.get("title", ""))[:80]
        score = item.get("score", 0)
        url = item.get("url", "")
        top_rows += f'<tr><td>{i}</td><td>{score}</td><td><a href="{url}" target="_blank">{title}</a></td></tr>'

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>News Radar — Análisis de Tendencias</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f1117; color: #e0e0e0; padding: 20px; }}
h1 {{ color: #fff; margin-bottom: 8px; }}
h2 {{ color: #8ab4f8; margin: 30px 0 15px; border-bottom: 1px solid #333; padding-bottom: 8px; }}
.subtitle {{ color: #888; margin-bottom: 30px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 16px; }}
.card {{ background: #1a1d27; border-radius: 8px; padding: 16px; }}
.card h3 {{ color: #fff; margin-bottom: 8px; }}
.card .meta {{ color: #888; font-size: 0.85em; margin-bottom: 8px; }}
.card p {{ color: #aaa; font-size: 0.9em; line-height: 1.5; }}
.tags {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }}
.tag {{ background: #2a2d3a; color: #8ab4f8; padding: 3px 10px; border-radius: 12px; font-size: 0.8em; }}
table {{ width: 100%; border-collapse: collapse; background: #1a1d27; border-radius: 8px; overflow: hidden; }}
th {{ background: #2a2d3a; color: #8ab4f8; padding: 10px; text-align: left; font-size: 0.85em; }}
td {{ padding: 8px 10px; border-bottom: 1px solid #2a2d3a; font-size: 0.85em; }}
td.desc {{ color: #888; max-width: 300px; }}
a {{ color: #8ab4f8; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
.bar-bg {{ background: #2a2d3a; border-radius: 4px; height: 22px; width: 120px; }}
.bar {{ background: linear-gradient(90deg, #2ecc71, #8ab4f8); border-radius: 4px; height: 22px; color: #fff; font-size: 0.75em; display: flex; align-items: center; justify-content: center; min-width: 30px; }}
.insights {{ background: #1a1d27; border-radius: 8px; padding: 16px; }}
.insights li {{ margin: 8px 0; line-height: 1.5; }}
.risks li {{ color: #e74c3c; }}
.hype-container {{ background: #1a1d27; border-radius: 8px; padding: 20px; text-align: center; }}
svg text {{ font-family: -apple-system, sans-serif; }}
</style>
</head>
<body>
<h1>📡 News Radar — Análisis de Tendencias</h1>
<p class="subtitle">Vigilancia Tecnológica · Análisis Histórico</p>

<h2>🗺️ Mapa de Tendencias</h2>
<table>
<thead><tr><th>Tendencia</th><th>Dirección</th><th>Momentum</th><th>Etapa Gartner</th><th>Descripción</th></tr></thead>
<tbody>{trend_rows}</tbody>
</table>

<h2>📊 Ciclo Hype (Gartner)</h2>
<div class="hype-container">{hype_svg}</div>

<h2>🧩 Clusters Temáticos</h2>
<div class="grid">{cluster_cards}</div>

<h2>💡 Insights Clave</h2>
<div class="insights"><ul>{insights_html}</ul></div>

<h2>🎯 Recomendaciones</h2>
<div class="insights"><ul>{recs_html}</ul></div>

<h2>⚠️ Señales de Riesgo</h2>
<div class="insights risks"><ul>{risks_html}</ul></div>

<h2>📰 Top Artículos</h2>
<table>
<thead><tr><th>#</th><th>Score</th><th>Título</th></tr></thead>
<tbody>{top_rows}</tbody>
</table>

</body>
</html>"""


def _build_hype_cycle_svg(hype_items: list[dict]) -> str:
    """Build a simple SVG hype cycle curve with trend positions."""
    # Gartner curve points (x positions for each stage)
    stage_x = {
        "innovation_trigger": 80,
        "peak_of_inflated_expectations": 200,
        "trough_of_disillusionment": 350,
        "slope_of_enlightenment": 500,
        "plateau_of_productivity": 650,
    }
    stage_y = {
        "innovation_trigger": 250,
        "peak_of_inflated_expectations": 60,
        "trough_of_disillusionment": 280,
        "slope_of_enlightenment": 160,
        "plateau_of_productivity": 120,
    }

    # SVG curve
    curve = (
        '<path d="M 40,300 C 80,300 120,50 200,50 '
        'C 280,50 300,310 350,310 '
        'C 400,310 450,150 500,150 '
        'C 550,150 600,120 700,120" '
        'fill="none" stroke="#444" stroke-width="2" stroke-dasharray="6,4"/>'
    )

    # Stage labels
    labels = ""
    for stage, label in [
        ("innovation_trigger", "Innovation\\nTrigger"),
        ("peak_of_inflated_expectations", "Peak of\\nExpectations"),
        ("trough_of_disillusionment", "Trough of\\nDisillusionment"),
        ("slope_of_enlightenment", "Slope of\\nEnlightenment"),
        ("plateau_of_productivity", "Plateau of\\nProductivity"),
    ]:
        x = stage_x[stage]
        parts = label.split("\\n")
        labels += f'<text x="{x}" y="330" fill="#666" font-size="10" text-anchor="middle">'
        for j, part in enumerate(parts):
            labels += f'<tspan x="{x}" dy="{12 if j else 0}">{part}</tspan>'
        labels += "</text>"

    # Plot trends on the curve
    dots = ""
    colors = ["#2ecc71", "#3498db", "#e74c3c", "#f39c12", "#9b59b6", "#1abc9c"]
    for i, item in enumerate(hype_items):
        stage = item.get("maturity_stage", "")
        topic = item.get("topic", "")[:30]
        x = stage_x.get(stage, 400)
        y = stage_y.get(stage, 200)
        # Offset to avoid overlap
        x += (i % 3) * 15 - 15
        y += (i // 3) * 20
        c = colors[i % len(colors)]
        dots += (
            f'<circle cx="{x}" cy="{y}" r="8" fill="{c}" opacity="0.9"/>'
            f'<text x="{x + 12}" y="{y + 4}" fill="{c}" font-size="11" font-weight="bold">{html_mod.escape(topic)}</text>'
        )

    return (
        f'<svg viewBox="0 0 750 360" width="100%" height="360">'
        f'<text x="375" y="20" fill="#888" font-size="13" text-anchor="middle">Gartner Hype Cycle</text>'
        f'{curve}{labels}{dots}</svg>'
    )


def main():
    parser = argparse.ArgumentParser(description="Visualize analysis results as HTML")
    parser.add_argument("--input", default="out/analysis_combined", help="Analysis directory")
    parser.add_argument("--out", default=None, help="Output HTML path (default: <input>/dashboard.html)")
    args = parser.parse_args()

    input_dir = Path(args.input)
    llm = load_json(input_dir / "llm_analysis.json")
    pbi = load_json(input_dir / "powerbi_data.json")

    if not llm and not pbi:
        print(f"No analysis files found in {input_dir}", file=sys.stderr)
        return 1

    html_content = build_html(llm, pbi)

    out_path = Path(args.out) if args.out else input_dir / "dashboard.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Dashboard saved to: {out_path}")
    print(f"Open in browser: file://{out_path.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
