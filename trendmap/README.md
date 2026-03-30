# Trend Map — Visualización Interactiva de Tendencias

## Ejecución rápida

```bash
cd news_radar_mvp

# 1. Estadísticas del corpus
python -m trendmap.scripts.compute_corpus_stats

# 2. Build completo (embeddings + UMAP + hulls + scores)
python -m trendmap.scripts.build_trendmap

# 3. Abrir dashboard
open trendmap/index.html
```

## Requisitos

- Python 3.11+
- `pip install umap-learn scipy boto3 pyyaml numpy scikit-learn`
- AWS credentials configuradas (para embeddings Bedrock)
- Si Bedrock no está disponible, usa TF-IDF como fallback automático

## Configuración

Editar `trendmap/config/trendmap.yml`:
- `embeddings.model_id`: modelo de Bedrock para embeddings
- `umap.*`: parámetros de UMAP
- `impact.*`: pesos para el score de impacto
- `paths.*`: rutas a los archivos de entrada

## Vistas del Dashboard

1. **Embedding Map**: scatter 2D (UMAP) con artículos y clusters, hulls por cluster
2. **Impacto vs Madurez**: bubble chart con clusters posicionados por impacto y horizonte
3. **Ciclo Hype**: curva Gartner con tendencias posicionadas
4. **Tabla**: lista filtrable de artículos con scores

## Métricas

### Impact Score (0-100)
- 45% avg relevance_score del cluster
- 25% volumen (log-normalized article count)
- 20% recencia (decay por días desde publicación)
- 10% señales extra (relevancia del cluster)

### Horizon Score (0-1)
- Mapeado desde maturity_stage del ciclo Gartner
- innovation_trigger=0.1, peak=0.3, trough=0.5, slope=0.7, plateau=0.9
