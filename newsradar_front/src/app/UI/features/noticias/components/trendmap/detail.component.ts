import { DecimalPipe } from '@angular/common';
import { Component, computed, input, signal } from '@angular/core';
import { ScoreBreakdown, TrendmapArticle, TrendmapCluster } from '../../../../../domain/noticias/models';

type SortField = 'title' | 'source' | 'date' | 'score';
type SortDir = 'asc' | 'desc';

@Component({
  selector: 'app-trendmap-detail',
  standalone: true,
  imports: [DecimalPipe],
  template: `
    <div class="space-y-4">
      @if (cluster()) {
        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.18em] text-dark-muted">
                {{ cluster()!.category }}
              </p>
              <h4 class="mt-2 text-xl font-semibold text-dark-text">{{ cluster()!.label }}</h4>
              <p class="mt-2 text-sm text-dark-muted">{{ cluster()!.subtitle }}</p>
              @if (cluster()!.comparative_signal) {
                <p class="mt-2 text-xs text-dark-muted">
                  Estado {{ cluster()!.comparative_signal!.status }} frente al snapshot previo ·
                  estabilidad {{ (cluster()!.comparative_signal!.stability_score ?? 0) | number:'1.0-0' }} ·
                  historial {{ cluster()!.history_depth ?? 1 }}
                </p>
              }
            </div>
            <div class="flex flex-wrap gap-2">
              <span class="rounded-full border border-dark-border bg-dark-bg px-3 py-1 text-xs text-dark-muted">
                {{ cluster()!.hype_stage }}
              </span>
              <span class="rounded-full border border-dark-border bg-dark-bg px-3 py-1 text-xs text-dark-muted">
                {{ cluster()!.maturity_stage }}
              </span>
            </div>
          </div>

          <div class="mt-4 grid gap-4 lg:grid-cols-4">
            <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
              <p class="text-xs uppercase tracking-wide text-dark-muted">Impacto</p>
              <p class="mt-2 text-2xl font-semibold text-dark-text">{{ cluster()!.impact_score | number:'1.0-0' }}</p>
            </div>
            <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
              <p class="text-xs uppercase tracking-wide text-dark-muted">Madurez</p>
              <p class="mt-2 text-2xl font-semibold text-dark-text">{{ cluster()!.maturity_score | number:'1.0-0' }}</p>
            </div>
            <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
              <p class="text-xs uppercase tracking-wide text-dark-muted">Dinamica</p>
              <p class="mt-2 text-2xl font-semibold text-dark-text">{{ cluster()!.momentum_score | number:'1.0-0' }}</p>
            </div>
            <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
              <p class="text-xs uppercase tracking-wide text-dark-muted">Novedad</p>
              <p class="mt-2 text-2xl font-semibold text-dark-text">{{ cluster()!.novelty_score | number:'1.0-0' }}</p>
            </div>
          </div>

          <div class="mt-4 grid gap-4 xl:grid-cols-[1.3fr_1fr]">
            <div class="space-y-4">
              <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-4">
                <h5 class="text-sm font-semibold text-dark-text">Que esta pasando</h5>
                <p class="mt-2 text-sm leading-6 text-dark-text/90">{{ cluster()!.what_is_happening }}</p>
                <p class="mt-3 text-sm leading-6 text-dark-muted">{{ cluster()!.why_it_matters }}</p>
                @if (cluster()!.evidence_line) {
                  <p class="mt-3 rounded-lg border border-dark-border bg-dark-surface px-3 py-2 text-sm text-dark-muted">
                    {{ cluster()!.evidence_line }}
                  </p>
                }
                <p class="mt-3 rounded-lg border border-dark-border bg-dark-surface px-3 py-2 text-sm text-dark-text/90">
                  {{ cluster()!.decision_prompt }}
                </p>
              </div>

              <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-4">
                <h5 class="text-sm font-semibold text-dark-text">Evidencia y analisis</h5>
                <p class="mt-2 text-sm leading-6 text-dark-muted">{{ cluster()!.rationale }}</p>
                <div class="mt-3 flex flex-wrap gap-2">
                  @for (match of cluster()!.taxonomy_matches; track match.name) {
                    <span class="rounded-full border border-dark-border bg-dark-surface px-3 py-1 text-xs text-dark-muted">
                      {{ match.name }} | {{ match.score * 100 | number:'1.0-0' }}
                    </span>
                  }
                </div>
                <div class="mt-3 space-y-2">
                  @for (evidence of cluster()!.insight_evidence; track evidence.type + evidence.detail) {
                    <div class="rounded-lg border border-dark-border bg-dark-surface/70 px-3 py-2 text-sm text-dark-text/90">
                      <span class="font-medium">{{ evidenceTypeLabel(evidence.type) }}</span>: {{ evidence.detail }}
                    </div>
                  }
                </div>
                @if ((cluster()!.impact_targets?.length ?? 0) > 0) {
                  <div class="mt-3 flex flex-wrap gap-2">
                    @for (target of (cluster()!.impact_targets ?? []).slice(0, 4); track target) {
                      <span class="rounded-full border border-emerald-500 bg-emerald-50 px-3 py-1 text-xs text-emerald-700">
                        {{ target }}
                      </span>
                    }
                  </div>
                }
              </div>
            </div>

            <div class="space-y-4">
              <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-4">
                <h5 class="text-sm font-semibold text-dark-text">Desglose del puntaje</h5>
                <div class="mt-3 space-y-3">
                  @for (entry of scoreSections(); track entry.label) {
                    <div class="rounded-lg border border-dark-border bg-dark-surface/70 p-3">
                      <div class="flex items-center justify-between gap-3">
                        <p class="text-sm font-medium text-dark-text">{{ entry.label }}</p>
                        <span class="text-xs text-dark-muted">{{ entry.breakdown.score | number:'1.0-0' }}</span>
                      </div>
                      @if (metricDescription(entry.label)) {
                        <p class="mt-1 text-xs leading-4 text-dark-muted italic">{{ metricDescription(entry.label) }}</p>
                      }
                      <p class="mt-2 text-xs leading-5 text-dark-muted">{{ entry.breakdown.formula }}</p>
                      <div class="mt-2 space-y-2">
                        @for (component of entry.breakdown.components.slice(0, 4); track component.name) {
                          <div>
                            <div class="flex items-center justify-between text-xs text-dark-muted">
                              <span>{{ scoreComponentLabel(component.name) }}</span>
                              <span>{{ component.value | number:'1.0-0' }}</span>
                            </div>
                            <div class="mt-1 h-1.5 rounded-full bg-dark-border">
                              <div class="h-full rounded-full bg-amber-500" [style.width.%]="component.value"></div>
                            </div>
                          </div>
                        }
                      </div>
                    </div>
                  }
                </div>
              </div>

              <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-4">
                <h5 class="text-sm font-semibold text-dark-text">Documentos representativos</h5>
                <div class="mt-3 space-y-3">
                  @for (doc of cluster()!.representative_documents; track doc.id) {
                    <div class="rounded-lg border border-dark-border bg-dark-surface/70 p-3">
                      <div class="flex items-start justify-between gap-3">
                        <a [href]="doc.url" target="_blank" rel="noopener noreferrer" class="text-sm font-medium text-dark-text hover:text-dark-accent">
                          {{ doc.title }}
                        </a>
                        <span class="text-xs text-dark-muted">{{ doc.score }}</span>
                      </div>
                      <p class="mt-1 text-xs text-dark-muted">{{ doc.source }} | {{ doc.date }}</p>
                      @if (doc.representative_reason) {
                        <p class="mt-2 text-xs text-dark-text/80">{{ doc.representative_reason }}</p>
                      }
                    </div>
                  }
                </div>
              </div>
            </div>
          </div>
        </section>
      }

      <section class="rounded-2xl border border-dark-border bg-dark-surface p-4">
        <div class="mb-4 flex items-center justify-between gap-4">
          <div>
            <h4 class="text-sm font-semibold text-dark-text">
              Documentos ({{ sortedArticles().length }})
            </h4>
            <p class="mt-1 text-xs text-dark-muted">
              Vista documental del cluster seleccionado o del conjunto filtrado.
            </p>
          </div>
        </div>

        @if (sortedArticles().length === 0) {
          <p class="text-dark-muted text-sm">No hay articulos para mostrar.</p>
        } @else {
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-dark-border">
                  <th class="cursor-pointer px-3 py-2 text-left font-medium text-dark-muted hover:text-dark-text" (click)="toggleSort('title')">Titulo {{ sortIndicator('title') }}</th>
                  <th class="cursor-pointer px-3 py-2 text-left font-medium text-dark-muted hover:text-dark-text" (click)="toggleSort('source')">Fuente {{ sortIndicator('source') }}</th>
                  <th class="px-3 py-2 text-left font-medium text-dark-muted">Razon</th>
                  <th class="cursor-pointer px-3 py-2 text-left font-medium text-dark-muted hover:text-dark-text" (click)="toggleSort('date')">Fecha {{ sortIndicator('date') }}</th>
                  <th class="cursor-pointer px-3 py-2 text-left font-medium text-dark-muted hover:text-dark-text" (click)="toggleSort('score')">Puntaje {{ sortIndicator('score') }}</th>
                </tr>
              </thead>
              <tbody>
                @for (article of sortedArticles(); track article.id) {
                  <tr class="border-b border-dark-border/50 align-top hover:bg-dark-bg/50 transition-colors">
                    <td class="px-3 py-3 text-dark-text">
                      <a [href]="article.url" target="_blank" rel="noopener noreferrer" class="hover:text-dark-accent">
                        {{ article.title }}
                      </a>
                      <p class="mt-1 text-xs text-dark-muted">{{ article.summary }}</p>
                    </td>
                    <td class="px-3 py-3 text-dark-muted">{{ article.source }}</td>
                    <td class="px-3 py-3 text-dark-muted">
                      {{ article.representative_reason ?? (article.duplicate_flag ? 'near-duplicate / soporte' : 'evidencia del cluster') }}
                    </td>
                    <td class="px-3 py-3 whitespace-nowrap text-dark-muted">{{ article.date }}</td>
                    <td class="px-3 py-3">
                      <span class="inline-flex items-center gap-2">
                        <span class="inline-block h-1.5 w-14 overflow-hidden rounded-full bg-dark-border">
                          <span class="block h-full rounded-full bg-dark-accent" [style.width.%]="article.score"></span>
                        </span>
                        <span class="text-xs text-dark-muted">{{ article.score | number:'1.0-0' }}</span>
                      </span>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      </section>
    </div>
  `,
})
export class TrendmapDetailComponent {
  readonly cluster = input<TrendmapCluster | null>(null);
  readonly articles = input<TrendmapArticle[]>([]);

  readonly sortField = signal<SortField>('score');
  readonly sortDir = signal<SortDir>('desc');

  readonly scoreSections = computed(() => {
    const cluster = this.cluster();
    if (!cluster) return [];
    const entries: Array<{ label: string; breakdown: ScoreBreakdown }> = [
      { label: 'Impacto', breakdown: cluster.impact_score_breakdown },
      { label: 'Madurez', breakdown: cluster.maturity_score_breakdown },
      { label: 'Dinamica', breakdown: cluster.momentum_score_breakdown },
      { label: 'Novedad', breakdown: cluster.novelty_score_breakdown },
      { label: 'Incertidumbre', breakdown: cluster.uncertainty_score_breakdown },
    ];
    if (cluster.persistence_score_breakdown) {
      entries.splice(1, 0, { label: 'Persistencia', breakdown: cluster.persistence_score_breakdown });
    }
    if (cluster.risk_severity_breakdown) {
      entries.unshift({ label: 'Severidad', breakdown: cluster.risk_severity_breakdown });
    }
    return entries;
  });

  readonly sortedArticles = computed(() => {
    const items = [...this.articles()];
    const field = this.sortField();
    const dir = this.sortDir();

    items.sort((a, b) => {
      let cmp = 0;
      switch (field) {
        case 'title':
          cmp = a.title.localeCompare(b.title);
          break;
        case 'source':
          cmp = a.source.localeCompare(b.source);
          break;
        case 'date':
          cmp = (a.date ?? '').localeCompare(b.date ?? '');
          break;
        case 'score':
          cmp = a.score - b.score;
          break;
      }
      return dir === 'asc' ? cmp : -cmp;
    });

    return items;
  });

  toggleSort(field: SortField): void {
    if (this.sortField() === field) {
      this.sortDir.set(this.sortDir() === 'asc' ? 'desc' : 'asc');
    } else {
      this.sortField.set(field);
      this.sortDir.set(field === 'score' ? 'desc' : 'asc');
    }
  }

  sortIndicator(field: SortField): string {
    if (this.sortField() !== field) return '';
    return this.sortDir() === 'asc' ? '^' : 'v';
  }

  scoreComponentLabel(rawName: string): string {
    const aliases: Record<string, string> = {
      recent_share: 'Participacion reciente',
      source_diversity: 'Diversidad de fuentes',
      stage_signal: 'Senal por etapa',
      avg_score: 'Calidad promedio',
      recency: 'Recencia',
      growth: 'Crecimiento',
      acceleration: 'Aceleracion',
      authority: 'Autoridad de fuentes',
      relevance: 'Relevancia',
      scale: 'Escala del cluster',
      size: 'Tamano del cluster',
      coherence: 'Coherencia',
      novelty: 'Novedad',
      uncertainty: 'Incertidumbre',
      persistence: 'Persistencia',
      taxonomy_focus: 'Foco taxonomico',
      transversality: 'Transversalidad',
      adoption: 'Adopcion',
      recurrence: 'Recurrencia',
      visibility: 'Visibilidad',
      materiality: 'Materialidad',
      duplicate_pressure: 'Presion por duplicados',
      low_recurrence: 'Baja recurrencia',
      low_authority: 'Baja autoridad',
      low_coherence: 'Baja coherencia',
      low_taxonomy_focus: 'Bajo foco taxonomico',
      low_scale: 'Escala pequena',
      low_diversity: 'Baja diversidad',
      low_activity: 'Baja actividad',
      low_score: 'Bajo puntaje',
      active_months: 'Meses activos',
      volume: 'Volumen documental',
      coverage: 'Cobertura',
      methodology: 'Metodologia',
      tempo: 'Tempo y ritmo',
      exploratory_signal: 'Senal exploratoria',
      small_scale: 'Escala pequena',
      uncertainty_penalty: 'Penalizacion por incertidumbre',
    };

    if (aliases[rawName]) {
      return aliases[rawName];
    }

    return rawName
      .replaceAll('_', ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  metricDescription(metricName: string): string {
    const descriptions: Record<string, string> = {
      'Impacto': 'Mide la potencial repercusion e importancia estrategica del cluster en el negocio y tecnologia',
      'Madurez': 'Mide el grado de adoption, recurrencia y consolidacion de la tematica en el tiempo',
      'Dinamica': 'Mide la intensidad reciente, crecimiento acelerado y visibilidad emergente del cluster',
      'Novedad': 'Mide el nivel de exploracion, recencia y baja recurrencia historica del tema',
      'Incertidumbre': 'Mide el nivel de exploracion, baja coherencia y duplicidad presente en la senal',
      'Severidad': 'Mide la potencial severidad y materialidad de un riesgo emergente',
      'Persistencia': 'Mide la estabilidad temporal y persistencia del riesgo en el ecosistema',
    };

    return descriptions[metricName] ?? '';
  }

  evidenceTypeLabel(type: string): string {
    const labels: Record<string, string> = {
      'Coverage': 'Cobertura',
      'Methodology': 'Metodologia',
      'Tempo': 'Tempo y ritmo',
      'Trend': 'Tendencia',
      'Pattern': 'Patron',
      'Signal': 'Senal',
      'Risk': 'Riesgo',
      'Opportunity': 'Oportunidad',
      'Insight': 'Insight',
      'Evidence': 'Evidencia',
      'Adoption': 'Adopcion',
      'Growth': 'Crecimiento',
      'Stability': 'Estabilidad',
    };

    return labels[type] ?? type.replaceAll('_', ' ');
  }
}
