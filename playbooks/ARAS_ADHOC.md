# Playbook: ARAS Ad-Hoc (Empresa + Rango)

## Propósito

Ejecutar una consulta ad-hoc para encontrar noticias relacionadas con una empresa específica en un rango de fechas. Solo noticias (news), no papers/repos/patentes.

## Entradas

| Parámetro | Tipo | Requerido | Ejemplo |
|-----------|------|-----------|---------|
| `--company` | string | Sí | `"Bancolombia"` |
| `--date-from` | YYYY-MM-DD | Sí | `2026-01-01` |
| `--date-to` | YYYY-MM-DD | Sí | `2026-03-15` |
| `--topk-per-source` | int | No (default: 5) | `10` |
| `--max-candidates-total` | int | No (default: 50) | `100` |

## Salidas

- `out/aras_adhoc/articles.jsonl` — Artículos extraídos con provenance
- `out/aras_adhoc/run_report.json` — Reporte con `adhoc_summary`

Cada documento incluye:
```json
{
  "origin": "adhoc_query",
  "query_type": "aras",
  "query_terms": ["Bancolombia"],
  "query_range": {"from": "2026-01-01", "to": "2026-03-15"}
}
```

## Comando

```bash
python -m extractor.main --catalog ../catalog.yaml \
  --focus aras_news --adhoc \
  --company "Bancolombia" \
  --date-from 2026-01-01 --date-to 2026-03-15 \
  --topk-per-source 5 --max-candidates-total 50 \
  --out out/aras_adhoc --debug
```

## Flujo interno

1. Descubre items de todas las fuentes habilitadas (RSS/scrape)
2. Filtra por rango de fechas (`date_from` / `date_to`)
3. Aplica matching metadata-only: busca nombre de empresa en `title`
4. Selecciona top-K por fuente, luego top-K global
5. Fetch completo solo de los candidatos seleccionados
6. Extrae texto, deduplica, persiste

## Criterios de matching

- Normalización: lowercase + strip accents + collapse whitespace
- Match en title: 2 puntos; match en snippet: 1 punto
- Score normalizado a 0-1
- Solo candidatos con score > 0 pasan

## Troubleshooting

- **0 candidatos**: Verificar que la empresa aparece en títulos de las fuentes del catálogo. Probar con `--dry-run` primero.
- **Muchos errores HTTP**: Algunas fuentes pueden estar bloqueadas. Revisar `run_report.json` → `by_source`.
- **Fechas no filtran**: Verificar formato YYYY-MM-DD. Items sin `published_at` se incluyen por defecto.
