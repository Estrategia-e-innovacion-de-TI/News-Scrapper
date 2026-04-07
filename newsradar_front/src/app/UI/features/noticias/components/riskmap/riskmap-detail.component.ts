import { DecimalPipe } from '@angular/common';
import { Component, input } from '@angular/core';

import { RiskmapCluster, TrendmapArticle } from '../../../../../domain/noticias/models';

interface ScoreRow {
  label: string;
  score: number;
  formula: string;
}

@Component({
  selector: 'app-riskmap-detail',
  standalone: true,
  imports: [DecimalPipe],
  template: `
    <div class="space-y-6">
      @if (cluster()) {
        <div class="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
            <div class="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p class="text-xs uppercase tracking-[0.18em] text-dark-muted">{{ cluster()!.dominant_risk || cluster()!.category }}</p>
                <h4 class="mt-2 text-xl font-semibold text-dark-text">{{ cluster()!.label }}</h4>
                <p class="mt-2 text-sm text-dark-muted">{{ cluster()!.subtitle }}</p>
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
                <p class="text-xs uppercase tracking-wide text-dark-muted">Impacto</p>
                <p class="mt-2 text-2xl font-semibold text-dark-text">{{ cluster()!.impact_score | number:'1.0-0' }}</p>
              </div>
              <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
                <p class="text-xs uppercase tracking-wide text-dark-muted">Persistencia</p>
                <p class="mt-2 text-2xl font-semibold text-dark-text">{{ cluster()!.persistence_score | number:'1.0-0' }}</p>
              </div>
              <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
                <p class="text-xs uppercase tracking-wide text-dark-muted">Momentum</p>
                <p class="mt-2 text-2xl font-semibold text-dark-text">{{ cluster()!.momentum_score | number:'1.0-0' }}</p>
              </div>
            </div>

            <div class="mt-4 space-y-4">
              <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-4">
                <h5 class="text-sm font-semibold text-dark-text">Que esta pasando</h5>
                <p class="mt-2 text-sm leading-6 text-dark-text/90">{{ cluster()!.what_is_happening }}</p>
                <p class="mt-3 text-sm leading-6 text-dark-muted">{{ cluster()!.why_it_matters }}</p>
                <p class="mt-3 rounded-lg border border-dark-border bg-dark-surface px-3 py-2 text-sm text-dark-text/90">
                  {{ cluster()!.decision_prompt }}
                </p>
              </div>

              <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-4">
                <h5 class="text-sm font-semibold text-dark-text">Evidencia y scoring</h5>
                <p class="mt-2 text-sm leading-6 text-dark-muted">{{ cluster()!.rationale }}</p>
                <div class="mt-3 flex flex-wrap gap-2">
                  @for (match of cluster()!.taxonomy_matches.slice(0, 5); track match.name) {
                    <span class="rounded-full border border-dark-border bg-dark-surface px-3 py-1 text-xs text-dark-muted">
                      {{ match.name }} | {{ match.score * 100 | number:'1.0-0' }}
                    </span>
                  }
                </div>
                <div class="mt-3 space-y-3">
                  @for (item of scoreRows(); track item.label) {
                    <div class="rounded-lg border border-dark-border bg-dark-surface/70 p-3">
                      <div class="flex items-center justify-between gap-3">
                        <p class="text-sm font-medium text-dark-text">{{ item.label }}</p>
                        <span class="text-xs text-dark-muted">{{ item.score | number:'1.0-0' }}</span>
                      </div>
                      <p class="mt-1 text-xs leading-5 text-dark-muted">{{ item.formula }}</p>
                    </div>
                  }
                </div>
              </div>
            </div>
          </section>

          <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
            <h4 class="text-sm font-semibold text-dark-text">Documentos representativos</h4>
            <div class="mt-4 space-y-3">
              @for (doc of cluster()!.representative_documents.slice(0, 5); track doc.id) {
                <div class="rounded-xl border border-dark-border bg-dark-bg/60 p-3">
                  <div class="flex items-start justify-between gap-3">
                    <a [href]="doc.url" target="_blank" rel="noopener noreferrer" class="text-sm font-medium text-dark-text hover:text-dark-accent">
                      {{ doc.title }}
                    </a>
                    <span class="text-xs text-dark-muted">{{ doc.score | number:'1.0-0' }}</span>
                  </div>
                  <p class="mt-1 text-xs text-dark-muted">{{ doc.source }} | {{ doc.date }}</p>
                  @if (doc.representative_reason) {
                    <p class="mt-2 text-xs text-dark-text/85">{{ doc.representative_reason }}</p>
                  }
                </div>
              }
            </div>
          </section>
        </div>
      }

      <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
        <h4 class="text-sm font-semibold text-dark-text">Documentos ({{ documents().length }})</h4>
        <div class="mt-4 overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-dark-border">
                <th class="px-3 py-2 text-left font-medium text-dark-muted">Documento</th>
                <th class="px-3 py-2 text-left font-medium text-dark-muted">Fuente</th>
                <th class="px-3 py-2 text-left font-medium text-dark-muted">Cluster</th>
                <th class="px-3 py-2 text-left font-medium text-dark-muted">Fecha</th>
                <th class="px-3 py-2 text-left font-medium text-dark-muted">Score</th>
              </tr>
            </thead>
            <tbody>
              @for (doc of documents(); track doc.id) {
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
}
