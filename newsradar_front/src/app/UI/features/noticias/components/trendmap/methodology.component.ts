import { Component } from '@angular/core';

@Component({
  selector: 'app-trendmap-methodology',
  standalone: true,
  template: `
    <div class="bg-dark-surface border border-dark-border rounded-lg p-6 space-y-6 max-w-3xl">
      <h4 class="text-lg font-semibold text-dark-text">Metodología del Trendmap</h4>

      <p class="text-dark-muted text-sm leading-relaxed">
        El mapa de tendencias se genera mediante un pipeline automatizado que combina
        técnicas de procesamiento de lenguaje natural, reducción de dimensionalidad y
        clustering no supervisado para identificar y visualizar patrones temáticos en
        noticias y papers académicos.
      </p>

      <!-- Step 1: Embeddings -->
      <section class="border-l-2 border-dark-accent pl-4">
        <h5 class="text-sm font-semibold text-dark-text mb-1">1. Embeddings Semánticos</h5>
        <p class="text-dark-muted text-sm leading-relaxed">
          Cada artículo se convierte en un vector numérico de alta dimensión usando
          Amazon Bedrock Titan Embed v2. Estos embeddings capturan el significado
          semántico del texto, permitiendo medir similitud entre documentos.
          Cuando Bedrock no está disponible, se usa TF-IDF como fallback.
        </p>
      </section>

      <!-- Step 2: UMAP -->
      <section class="border-l-2 border-dark-accent pl-4">
        <h5 class="text-sm font-semibold text-dark-text mb-1">2. Reducción Dimensional (UMAP)</h5>
        <p class="text-dark-muted text-sm leading-relaxed">
          Los embeddings de alta dimensión se proyectan a 2 dimensiones usando UMAP
          (Uniform Manifold Approximation and Projection) con métrica coseno.
          Se aplica PCA previo para reducir ruido. El resultado son las coordenadas
          (x, y) que posicionan cada artículo en el mapa, preservando las relaciones
          de vecindad del espacio original.
        </p>
      </section>

      <!-- Step 3: HDBSCAN -->
      <section class="border-l-2 border-dark-accent pl-4">
        <h5 class="text-sm font-semibold text-dark-text mb-1">3. Clustering (HDBSCAN)</h5>
        <p class="text-dark-muted text-sm leading-relaxed">
          Los artículos se agrupan automáticamente usando HDBSCAN (Hierarchical
          Density-Based Spatial Clustering of Applications with Noise), un algoritmo
          que detecta clusters de densidad variable sin requerir un número predefinido
          de grupos. Los artículos que no pertenecen a ningún cluster se marcan como ruido.
        </p>
      </section>

      <!-- Step 4: LLM Labeling -->
      <section class="border-l-2 border-dark-accent pl-4">
        <h5 class="text-sm font-semibold text-dark-text mb-1">4. Etiquetado con LLM</h5>
        <p class="text-dark-muted text-sm leading-relaxed">
          Cada cluster se etiqueta usando Claude Haiku (Amazon Bedrock), que genera
          un nombre descriptivo, categoría, resumen, keywords y nivel de relevancia
          en español. Esto permite interpretar cada grupo temático de forma intuitiva.
        </p>
      </section>

      <!-- Step 5: Metrics -->
      <section class="border-l-2 border-dark-accent pl-4">
        <h5 class="text-sm font-semibold text-dark-text mb-1">5. Métricas y Visualización</h5>
        <p class="text-dark-muted text-sm leading-relaxed">
          Para cada cluster se calculan: polígono convex hull (envolvente visual),
          impact score (0-100), horizon score (0-1 mapeado a etapas Gartner del
          Hype Cycle). Los super-clusters agrupan clusters por categoría para una
          vista de alto nivel.
        </p>
      </section>

      <!-- Legend -->
      <div class="bg-dark-bg border border-dark-border rounded-lg p-4 mt-4">
        <h5 class="text-xs font-semibold text-dark-muted uppercase tracking-wide mb-2">
          Etapas del Hype Cycle (Gartner)
        </h5>
        <ol class="text-dark-muted text-sm space-y-1 list-decimal list-inside">
          <li>Innovation Trigger — Tecnología emergente, primeras pruebas de concepto</li>
          <li>Peak of Inflated Expectations — Expectativas exageradas, alta cobertura mediática</li>
          <li>Trough of Disillusionment — Desilusión, fracasos iniciales, interés decae</li>
          <li>Slope of Enlightenment — Maduración, casos de uso reales emergen</li>
          <li>Plateau of Productivity — Adopción generalizada, beneficios demostrados</li>
        </ol>
      </div>
    </div>
  `,
})
export class TrendmapMethodologyComponent {}
