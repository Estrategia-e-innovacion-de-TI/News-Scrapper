import { DecimalPipe } from '@angular/common';
import { Component, computed, input } from '@angular/core';
import {
  FiltersMetadata,
  MethodologyBlock,
  QualityChecks,
} from '../../../../../domain/noticias/models';

@Component({
  selector: 'app-trendmap-methodology',
  standalone: true,
  imports: [DecimalPipe],
  template: `
    <div class="max-w-5xl space-y-6">
      <section class="rounded-2xl border border-dark-border bg-dark-surface p-6">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h4 class="text-lg font-semibold text-dark-text">Metodologia analitica</h4>
            <p class="mt-2 max-w-3xl text-sm leading-6 text-dark-muted">
              El backend construye el snapshot con representacion documental hibrida,
              clusterizacion explicable y scoring multi-factor. El frontend solo visualiza
              payloads preparados.
            </p>
          </div>
          <span class="rounded-full border border-dark-border bg-dark-bg px-3 py-1 text-xs text-dark-muted">
            {{ methodology()?.methodology_version ?? qualityChecks()?.methodology_version ?? 'analytics_methodology_v3' }}
          </span>
        </div>
      </section>

      <div class="grid gap-6 xl:grid-cols-3">
        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h5 class="text-sm font-semibold text-dark-text">Representacion</h5>
          <p class="mt-3 text-sm leading-6 text-dark-muted">
            {{ representationDescription() }}
          </p>
          @if (representationEntries().length > 0) {
            <div class="mt-4 space-y-2">
              @for (entry of representationEntries(); track entry.label) {
                <div class="rounded-xl border border-dark-border bg-dark-bg/70 px-3 py-2">
                  <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">
                    {{ entry.label }}
                  </p>
                  <p class="mt-1 text-sm text-dark-text">{{ entry.value }}</p>
                </div>
              }
            </div>
          }
        </section>

        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h5 class="text-sm font-semibold text-dark-text">Clusterizacion</h5>
          <p class="mt-3 text-sm leading-6 text-dark-muted">
            Se combinan espacio lexical/semantico, reduccion para coordenadas 2D y un
            algoritmo de clusterizacion con manejo de noise. Los clusters pequenos y de
            alta novedad se marcan como weak signals.
          </p>
          @if (clusteringEntries().length > 0) {
            <div class="mt-4 space-y-2">
              @for (entry of clusteringEntries(); track entry.label) {
                <div class="rounded-xl border border-dark-border bg-dark-bg/70 px-3 py-2">
                  <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">
                    {{ entry.label }}
                  </p>
                  <p class="mt-1 text-sm text-dark-text">{{ entry.value }}</p>
                </div>
              }
            </div>
          }
        </section>

        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h5 class="text-sm font-semibold text-dark-text">Calidad y cobertura</h5>
          @if (qualityChecks()) {
            <div class="mt-3 grid grid-cols-2 gap-3">
              <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
                <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Coherencia</p>
                <p class="mt-2 text-xl font-semibold text-dark-text">
                  {{ qualityChecks()!.cluster_coherence_avg | number:'1.0-0' }}
                </p>
              </div>
              <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
                <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Cobertura tax.</p>
                <p class="mt-2 text-xl font-semibold text-dark-text">
                  {{ qualityChecks()!.taxonomy_coverage | number:'1.0-0' }}%
                </p>
              </div>
              <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
                <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Keywords utiles</p>
                <p class="mt-2 text-xl font-semibold text-dark-text">
                  {{ qualityChecks()!.keyword_usefulness_ratio | number:'1.0-0' }}%
                </p>
              </div>
              <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
                <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Weak signals</p>
                <p class="mt-2 text-xl font-semibold text-dark-text">
                  {{ qualityChecks()!.weak_signal_clusters }}
                </p>
              </div>
            </div>
          } @else {
            <p class="mt-3 text-sm leading-6 text-dark-muted">
              El snapshot incluye cluster coherence, calidad promedio, ratio de no cluster,
              coverage taxonomico y ratio de keywords utiles para monitorear degradacion.
            </p>
          }
        </section>
      </div>

      <section class="rounded-2xl border border-dark-border bg-dark-surface p-6">
        <h5 class="text-sm font-semibold text-dark-text">Formulas interpretables</h5>
        <div class="mt-4 grid gap-4 lg:grid-cols-2">
          @for (formula of formulas; track formula.label) {
            <div class="rounded-2xl border border-dark-border bg-dark-bg/60 p-4">
              <p class="text-sm font-semibold text-dark-text">{{ formula.label }}</p>
              <p class="mt-2 text-sm leading-6 text-dark-muted">{{ formula.description }}</p>
              <p class="mt-3 rounded-xl border border-dark-border bg-dark-surface px-3 py-2 text-xs text-dark-text/90">
                {{ formula.value }}
              </p>
            </div>
          }
        </div>
      </section>

      @if (filtersMetadata()) {
        <section class="rounded-2xl border border-dark-border bg-dark-surface p-6">
          <h5 class="text-sm font-semibold text-dark-text">Espacio de filtros expuesto</h5>
          <div class="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div class="rounded-xl border border-dark-border bg-dark-bg/60 p-4">
              <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Categorias</p>
              <p class="mt-2 text-sm leading-6 text-dark-text">
                {{ filtersMetadata()!.categories.join(', ') || 'N/D' }}
              </p>
            </div>
            <div class="rounded-xl border border-dark-border bg-dark-bg/60 p-4">
              <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Source types</p>
              <p class="mt-2 text-sm leading-6 text-dark-text">
                {{ filtersMetadata()!.source_types.join(', ') || 'N/D' }}
              </p>
            </div>
            <div class="rounded-xl border border-dark-border bg-dark-bg/60 p-4">
              <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Maturity stages</p>
              <p class="mt-2 text-sm leading-6 text-dark-text">
                {{ joinStages(filtersMetadata()!.maturity_stages) }}
              </p>
            </div>
            <div class="rounded-xl border border-dark-border bg-dark-bg/60 p-4">
              <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Hype stages</p>
              <p class="mt-2 text-sm leading-6 text-dark-text">
                {{ joinStages(filtersMetadata()!.hype_stages) }}
              </p>
            </div>
          </div>
        </section>
      }
    </div>
  `,
})
export class TrendmapMethodologyComponent {
  readonly methodology = input<MethodologyBlock | null>(null);
  readonly qualityChecks = input<QualityChecks | null>(null);
  readonly filtersMetadata = input<FiltersMetadata | null>(null);

  readonly formulas = [
    {
      label: 'Impacto trend',
      description:
        'Combina relevancia, autoridad de fuentes, diversidad, escala del cluster, foco taxonomico y transversalidad.',
      value:
        '0.28 relevancia + 0.16 autoridad + 0.14 diversidad + 0.14 escala + 0.14 foco taxonomico + 0.14 transversalidad',
    },
    {
      label: 'Madurez trend',
      description:
        'Evita heuristicas arbitrarias: pondera recurrencia temporal, adopcion explicita, tamano, coherencia, autoridad y baja novedad.',
      value:
        '0.28 recurrencia + 0.20 adopcion + 0.16 escala + 0.14 coherencia + 0.12 autoridad + 0.10 baja novedad',
    },
    {
      label: 'Momentum',
      description:
        'Mide intensidad reciente a partir de crecimiento, aceleracion, share reciente y visibilidad observada en el cluster.',
      value: '0.40 crecimiento + 0.25 aceleracion + 0.20 recencia + 0.15 visibilidad',
    },
    {
      label: 'Novedad e incertidumbre',
      description:
        'La novedad favorece recencia y baja recurrencia; la incertidumbre sube con exploracion, baja coherencia, baja autoridad y duplicidad.',
      value:
        'Novedad: 0.45 recencia + 0.30 baja recurrencia + 0.15 exploracion + 0.10 escala pequena. Incertidumbre: 0.30 exploracion + 0.25 baja coherencia + 0.20 baja autoridad + 0.15 duplicidad + 0.10 bajo foco taxonomico',
    },
    {
      label: 'Severidad y persistencia de riesgo',
      description:
        'El mapa de riesgos usa formulas paralelas para severidad potencial y persistencia, de modo que el mapa sea comparable pero orientado a materialidad.',
      value:
        'Severidad: 0.26 relevancia + 0.24 materialidad + 0.18 autoridad + 0.16 diversidad + 0.16 foco taxonomico. Persistencia: 0.40 recurrencia + 0.20 escala + 0.15 autoridad + 0.15 coherencia + 0.10 diversidad',
    },
  ];

  readonly representationEntries = computed(() => {
    const representation = this.methodology()?.representation ?? {};
    return Object.entries(representation).map(([key, value]) => ({
      label: key.replaceAll('_', ' '),
      value: Array.isArray(value) ? value.join(', ') : String(value),
    }));
  });

  readonly clusteringEntries = computed(() => {
    const clustering = this.methodology()?.clustering ?? {};
    return Object.entries(clustering).map(([key, value]) => ({
      label: key.replaceAll('_', ' '),
      value: String(value),
    }));
  });

  representationDescription(): string {
    const representation = this.methodology()?.representation;
    if (!representation) {
      return 'Cada documento se representa con titulo, excerpt, texto normalizado, keywords, taxonomia y metadata de fuente. El feature space puede combinar TF-IDF, embeddings y senales auxiliares.';
    }
    return (
      String(representation['document_text'] ?? '') ||
      'Cada documento se representa con texto enriquecido y metadata contextual.'
    );
  }

  joinStages(values: string[]): string {
    return values.map((value) => value.replaceAll('_', ' ')).join(', ');
  }
}
