import { DecimalPipe } from '@angular/common';
import { Component, computed, input, signal } from '@angular/core';

import { RiskmapCluster, TrendmapArticle } from '../../../../../domain/noticias/models';

interface ScoreRow {
  label: string;
  score: number;
  formula: string;
}

type SortField = 'title' | 'source' | 'date' | 'score';
type SortDir = 'asc' | 'desc';

@Component({
  selector: 'app-riskmap-detail',
  standalone: true,
  imports: [DecimalPipe],
  template: `
    <div class="space-y-4">
      @if (cluster()) {
        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.18em] text-dark-muted">
                {{ cluster()!.dominant_risk || cluster()!.category }}
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
              <span [class]="stageBadge(cluster()!.hype_stage)">{{ stageLabel(cluster()!.hype_stage) }}</span>
              <span class="rounded-full border border-dark-border bg-dark-bg px-3 py-1 text-xs text-dark-muted">
                {{ cluster()!.maturity_stage.replaceAll('_', ' ') }}
              </span>
            </div>
          </div>

          <div class="mt-4 grid gap-4 lg:grid-cols-4">
            <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
              <p class="text-xs uppercase tracking-wide text-dark-muted">Severidad</p>
              <p class="mt-2 text-2xl font-semibold text-dark-text">{{ cluster()!.risk_severity | number:'1.0-0' }}</p>
            </div>
            <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
              <p class="text-xs uppercase tracking-wide text-dark-muted">Persistencia</p>
              <p class="mt-2 text-2xl font-semibold text-dark-text">{{ cluster()!.persistence_score | number:'1.0-0' }}</p>
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
                @if (cluster()!.insight_evidence.length > 0) {
                  <div class="mt-3 space-y-2">
                    @for (evidence of cluster()!.insight_evidence; track evidence.type + evidence.detail) {
                      <div class="rounded-lg border border-dark-border bg-dark-surface/70 px-3 py-2 text-sm text-dark-text/90">
                        <span class="font-medium">{{ evidenceTypeLabel(evidence.type) }}</span>: {{ evidence.detail }}
                      </div>
                    }
                  </div>
                }
                @if ((cluster()!.impact_targets?.length ?? 0) > 0) {
                  <div class="mt-3 flex flex-wrap gap-2">
                    @for (target of (cluster()!.impact_targets ?? []).slice(0, 4); track target) {
                      <span class="rounded-full border border-rose-400 bg-rose-50 px-3 py-1 text-xs text-rose-700">
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
                  @for (entry of scoreRows(); track entry.label) {
                    <div class="rounded-lg border border-dark-border bg-dark-surface/70 p-3">
                      <div class="flex items-center justify-between gap-3">
                        <div>
                          <p class="text-sm font-medium text-dark-text">{{ entry.label }}</p>
                          <p class="mt-0.5 text-xs italic text-dark-muted">{{ metricDescription(entry.label) }}</p>
                        </div>
                        <div class="flex shrink-0 flex-col items-end gap-1">
                          <span class="text-sm font-semibold text-dark-text">{{ entry.score | number:'1.0-0' }}</span>
                          <div class="h-1.5 w-16 overflow-hidden rounded-full bg-dark-border">
                            <div class="h-full rounded-full bg-amber-400" [style.width.%]="entry.score"></div>
                          </div>
                        </div>
                      </div>
                      @if (entry.formula) {
                        <p class="mt-1 text-xs leading-5 text-dark-muted">{{ entry.formula }}</p>
                      }
                    </div>
                  }
                </div>
              </div>

              <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-4">
                <h4 class="text-sm font-semibold text-dark-text">Documentos representativos</h4>
                <div class="mt-3 space-y-2">
                  @for (doc of cluster()!.representative_documents.slice(0, 5); track doc.id) {
                    <div class="rounded-xl border border-dark-border bg-dark-bg/60 p-3">
                      <div class="flex items-start justify-between gap-3">
                        <a [href]="doc.url" target="_blank" rel="noopener noreferrer" class="text-sm font-medium text-dark-text hover:text-dark-accent">
                          {{ doc.title }}
                        </a>
                        <span class="shrink-0 text-xs text-dark-muted">{{ doc.score | number:'1.0-0' }}</span>
                      </div>
                      <p class="mt-1 text-xs text-dark-muted">{{ doc.source }} | {{ doc.date }}</p>
                      @if (doc.representative_reason) {
                        <p class="mt-2 text-xs text-dark-text/85">{{ doc.representative_reason }}</p>
                      }
                    </div>
                  }
                </div>
              </div>
            </div>
          </div>
        </section>
      }

      <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <h4 class="text-sm font-semibold text-dark-text">Documentos ({{ documents().length }})</h4>
          <div class="flex gap-2 text-xs text-dark-muted">
            @for (col of sortCols; track col.field) {
              <button
                class="rounded-full border border-dark-border bg-dark-bg px-3 py-1 transition hover:text-dark-text"
                [class.border-yellow-400]="sortField() === col.field"
                [class.text-dark-text]="sortField() === col.field"
                type="button"
                (click)="toggleSort(col.field)"
              >
                {{ col.label }} {{ sortField() === col.field ? (sortDir() === 'asc' ? '↑' : '↓') : '' }}
              </button>
            }
          </div>
        </div>
        <div class="mt-4 overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-dark-border">
                <th class="px-3 py-2 text-left font-medium text-dark-muted">Documento</th>
                <th class="px-3 py-2 text-left font-medium text-dark-muted">Fuente</th>
                <th class="px-3 py-2 text-left font-medium text-dark-muted">Cluster</th>
                <th class="px-3 py-2 text-left font-medium text-dark-muted">Fecha</th>
                <th class="px-3 py-2 text-left font-medium text-dark-muted">Puntaje</th>
              </tr>
            </thead>
            <tbody>
              @for (doc of sortedDocuments(); track doc.id) {
                <tr class="border-b border-dark-border/50 align-top hover:bg-dark-bg/50">
                  <td class="px-3 py-3 text-dark-text">
                    <a [href]="doc.url" target="_blank" rel="noopener noreferrer" class="hover:text-dark-accent">{{ doc.title }}</a>
                    <p class="mt-1 text-xs text-dark-muted">{{ doc.summary }}</p>
                  </td>
                  <td class="px-3 py-3 text-dark-muted">{{ doc.source }}</td>
                  <td class="px-3 py-3 text-dark-muted">{{ doc.cluster_label ?? doc.cluster_id }}</td>
                  <td class="px-3 py-3 whitespace-nowrap text-dark-muted">{{ doc.date }}</td>
                  <td class="px-3 py-3 text-dark-muted">{{ doc.score | number:'1.0-0' }}</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </section>
    </div>
  `,
})
export class RiskmapDetailComponent {
  readonly cluster = input<RiskmapCluster | null>(null);
  readonly documents = input.required<TrendmapArticle[]>();
  readonly scoreRows = input.required<ScoreRow[]>();

  readonly sortField = signal<SortField>('score');
  readonly sortDir = signal<SortDir>('desc');

  readonly sortCols: Array<{ field: SortField; label: string }> = [
    { field: 'score', label: 'Puntaje' },
    { field: 'date', label: 'Fecha' },
    { field: 'source', label: 'Fuente' },
    { field: 'title', label: 'Titulo' },
  ];

  readonly sortedDocuments = computed(() => {
    const docs = [...this.documents()];
    const field = this.sortField();
    const dir = this.sortDir();
    return docs.sort((a, b) => {
      const av = a[field] as string | number;
      const bv = b[field] as string | number;
      if (av < bv) return dir === 'asc' ? -1 : 1;
      if (av > bv) return dir === 'asc' ? 1 : -1;
      return 0;
    });
  });

  toggleSort(field: SortField): void {
    if (this.sortField() === field) {
      this.sortDir.set(this.sortDir() === 'asc' ? 'desc' : 'asc');
    } else {
      this.sortField.set(field);
      this.sortDir.set('desc');
    }
  }

  stageLabel(value: string): string {
    return value.replaceAll('_', ' ');
  }

  stageBadge(value: string): string {
    const base = 'rounded-full border px-2 py-1 text-[10px] font-medium ';
    if (value === 'weak_signal') return base + 'border-yellow-500 bg-yellow-100 text-yellow-900';
    if (value === 'correction') return base + 'border-rose-500 bg-rose-50 text-rose-700';
    if (value === 'productive_adoption' || value === 'consolidation') return base + 'border-emerald-500 bg-emerald-50 text-emerald-700';
    return base + 'border-sky-500 bg-sky-50 text-sky-700';
  }

  metricDescription(label: string): string {
    const map: Record<string, string> = {
      Severidad: 'Impacto potencial del riesgo sobre la organizacion.',
      Persistencia: 'Recurrencia temporal y estabilidad de la señal.',
      Impacto: 'Nivel de consecuencias operativas y estrategicas.',
      Madurez: 'Grado de consolidacion del riesgo en el entorno.',
      Dinamica: 'Velocidad de aparicion y crecimiento documental.',
      Novedad: 'Que tan nueva o emergente es la señal.',
      Incertidumbre: 'Nivel de ambiguedad y falta de informacion.',
    };
    return map[label] ?? '';
  }

  evidenceTypeLabel(type: string): string {
    const map: Record<string, string> = {
      Coverage: 'Cobertura',
      Methodology: 'Metodologia',
      Tempo: 'Tempo y ritmo',
      Signal: 'Señal',
      Trend: 'Tendencia',
      Risk: 'Riesgo',
    };
    return map[type] ?? type;
  }
}
