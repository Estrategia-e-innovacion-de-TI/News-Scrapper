# Playbook: Onboarding de Nuevas Fuentes

## Propósito

Evaluar nuevas fuentes (news, repos, papers, patents) para inclusión en el catálogo. Genera un patch sin modificar el catálogo directamente.

## Entradas

Archivo `new_sources.yaml`:

```yaml
sources:
  - source_id: mi_fuente_news
    name: Mi Fuente de Noticias
    url: https://example.com
    type: news

  - source_id: mi_repo
    name: Mi Repositorio
    url: https://github.com/org/repo
    type: repo

  - source_id: mi_paper_source
    name: ArXiv Category
    url: https://arxiv.org/list/cs.AI/recent
    type: paper
```

## Salidas

- `out/source_eval/catalog_patch.yaml` — Patch para el catálogo
- `out/source_eval/source_scorecard.json` — Scorecard detallado
- `out/source_eval/samples/` — HTML de muestra (si aplica)

## Comando

```bash
python -m extractor.source_eval --input new_sources.yaml --out out/source_eval --debug
```

## Evaluación por tipo

### News

1. Detecta RSS/Atom/JSONFeed por `<link rel="alternate">` y rutas comunes (`/feed`, `/rss`)
2. Si no hay RSS, infiere selectores de listing/article (heurística)
3. Detecta `requires_playwright` (JS-heavy)
4. Detecta paywall/403
5. Valida con 3 artículos: reporta `text_len` promedio

### Repos

1. Clasifica provider conocido: `github`, `gitlab`, `huggingface`
2. Genera config de provider si aplica
3. Si no es conocido, marca `custom_pending`

### Papers

1. Clasifica provider conocido: `arxiv`, `semantic_scholar`
2. Genera config de provider si aplica
3. Si no es conocido, marca `custom_pending`

### Patents

1. Clasifica provider conocido: `google_patents`, `espacenet`
2. Genera config de provider si aplica
3. Si no es conocido, marca `custom_pending`

## Scorecard

```json
{
  "source_id": "mi_fuente_news",
  "type": "news",
  "rss_detected": true,
  "rss_url": "https://example.com/feed",
  "requires_playwright": false,
  "paywall_detected": false,
  "sample_articles": 3,
  "avg_text_len": 2500,
  "quality_hint": "ok",
  "recommendation": "add_to_catalog"
}
```

## Aplicar el patch

El patch NO se aplica automáticamente. Revisar y aplicar manualmente:

```bash
# Revisar
cat out/source_eval/catalog_patch.yaml

# Aplicar (manual)
# Copiar las entradas relevantes a catalog.yaml
```

## Troubleshooting

- **RSS no detectado**: Verificar manualmente si existe. Algunas fuentes usan rutas no estándar.
- **requires_playwright=true**: El sitio usa JS para renderizar contenido. Necesita Playwright.
- **paywall_detected=true**: El sitio bloquea acceso. Marcar como `gated` en el catálogo.
- **custom_pending**: Provider no reconocido. Requiere desarrollo custom.
