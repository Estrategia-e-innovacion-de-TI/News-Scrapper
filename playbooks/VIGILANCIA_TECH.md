# Playbook: Vigilancia Tecnológica

## Propósito

Monitoreo periódico de noticias, papers, repos y patentes relacionados con temas de vigilancia tecnológica.

## Horizontes de ejecución

| Tipo | Frecuencia | Comando |
|------|------------|---------|
| News | Semanal | `--focus vigilancia_news --days 7` |
| Papers (ArXiv) | Mensual | `--mode papers --since-days 30` |
| Repos (GitHub) | Mensual | `--mode repos --since-days 30` |
| Patentes | Bimensual/Trimestral | `--mode patents --since-days 90` |

## Flujo: News semanal

```bash
python -m extractor.main --catalog ../catalog.yaml \
  --focus vigilancia_news --days 7 \
  --out out/vigilancia_news_weekly --debug
```

No soporta `--adhoc`. Extrae de todas las fuentes habilitadas con focus `vigilancia`.

## Flujo: Papers/Repos/Patentes (Search → Ingest)

### Paso 1: Search

```bash
# Papers
python -m extractor.search --terms terms_vigilancia.yaml --mode papers \
  --since-days 30 --out out/search/papers

# Repos
python -m extractor.search --terms terms_vigilancia.yaml --mode repos \
  --since-days 30 --out out/search/repos

# Patentes
python -m extractor.search --terms terms_vigilancia.yaml --mode patents \
  --since-days 90 --out out/search/patents
```

Produce:
- `candidates.jsonl` — Candidatos filtrados
- `search_report.json` — Resumen

### Paso 2: Ingest

```bash
python -m extractor.main --catalog ../catalog.yaml \
  --candidates out/search/papers/candidates.jsonl \
  --out out/vigilancia_papers --debug
```

## Configuración de términos

Archivo `terms_vigilancia.yaml`:

```yaml
papers:
  terms:
    - "fraud detection deep learning"
    - "anomaly detection financial"
    - "risk management machine learning"
  filters:
    require_keywords_any: ["fraud", "risk", "anomaly"]

repos:
  terms:
    - "fraud-detection-ml"
    - "anomaly-detection"
    - "risk-scoring"
  filters:
    min_stars: 10
    updated_within_days: 90

patents:
  terms:
    - "fraud detection artificial intelligence"
    - "risk assessment machine learning"
  filters:
    date_window_months: 6
```

## Providers

| Modo | Provider | Notas |
|------|----------|-------|
| papers | ArXiv RSS | Confiable, ordenado por fecha |
| repos | GitHub API | Usa `GITHUB_TOKEN` si disponible |
| patents | Google Patents SERP | Limitado: SPA, puede requerir SerpAPI |

## Troubleshooting

- **GitHub rate limit**: Exportar `GITHUB_TOKEN=ghp_...`
- **Patents 0 resultados**: Google Patents es SPA. Considerar SerpAPI o Playwright.
- **Papers sin resultados**: Verificar términos en ArXiv. Usar términos en inglés.
