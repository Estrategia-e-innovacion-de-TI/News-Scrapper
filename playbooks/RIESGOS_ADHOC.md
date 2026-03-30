# Playbook: Riesgos Ad-Hoc (Términos + Rango)

## Propósito

Ejecutar una consulta ad-hoc para encontrar noticias relacionadas con términos de riesgo específicos en un rango de fechas. Solo noticias (news).

## Entradas

| Parámetro | Tipo | Requerido | Ejemplo |
|-----------|------|-----------|---------|
| `--terms` | string (comma-sep) | Sí | `"fraude,ransomware,near miss"` |
| `--date-from` | YYYY-MM-DD | Sí | `2025-12-01` |
| `--date-to` | YYYY-MM-DD | Sí | `2026-03-15` |
| `--topk-per-source` | int | No (default: 5) | `10` |
| `--max-candidates-total` | int | No (default: 50) | `100` |

## Salidas

- `out/riesgos_adhoc/articles.jsonl` — Artículos extraídos con provenance
- `out/riesgos_adhoc/run_report.json` — Reporte con `adhoc_summary`

Cada documento incluye:
```json
{
  "origin": "adhoc_query",
  "query_type": "riesgos",
  "query_terms": ["fraude", "ransomware", "near miss"],
  "query_range": {"from": "2025-12-01", "to": "2026-03-15"}
}
```

## Comando

```bash
python -m extractor.main --catalog ../catalog.yaml \
  --focus riesgos_news --adhoc \
  --terms "fraude,ransomware,near miss,operational error" \
  --date-from 2025-12-01 --date-to 2026-03-15 \
  --topk-per-source 5 --max-candidates-total 50 \
  --out out/riesgos_adhoc --debug
```

## Flujo interno

1. Descubre items de todas las fuentes habilitadas
2. Filtra por rango de fechas
3. Aplica matching metadata-only: busca términos en `title` y `snippet`
4. Selecciona top-K por fuente, luego top-K global
5. Fetch completo solo de los candidatos seleccionados
6. Extrae texto, deduplica, persiste

## Criterios de matching

- Términos separados por coma, cada uno normalizado
- Match en title: 2 puntos por término; match en snippet: 1 punto
- Score acumulativo normalizado a 0-1
- Más términos matched = mayor score

## Términos sugeridos por categoría

| Categoría | Términos |
|-----------|----------|
| Fraude | fraude, fraud, estafa, phishing, suplantación |
| Ciberseguridad | ransomware, malware, data breach, ciberataque |
| Operacional | near miss, operational error, falla operativa |
| Compliance | sanción, multa, regulador, incumplimiento |

## Troubleshooting

- **0 candidatos**: Verificar que los términos aparecen en títulos. Probar términos más genéricos.
- **Demasiados falsos positivos**: Usar términos más específicos o reducir `--max-candidates-total`.
- **Términos con espacios**: Usar comillas en el valor completo: `--terms "near miss,data breach"`.
