import { Component, input, signal } from '@angular/core';
import { DocumentResult } from '../../../../../domain/noticias/models';

@Component({
  selector: 'app-results-table',
  standalone: true,
  template: `
    @if (results().length === 0) {
      <p class="text-gray-500 text-sm">Sin resultados para los criterios especificados.</p>
    } @else {
      <div class="overflow-auto rounded-lg shadow-sm">
        <table class="w-full text-sm border-collapse">
          <thead>
            <tr class="bg-gray-100 text-left">
              <th class="px-3 py-2">#</th>
              <th class="px-3 py-2">Título</th>
              <th class="px-3 py-2">Medio</th>
              <th class="px-3 py-2">Fecha</th>
              <th class="px-3 py-2">Categoría</th>
              <th class="px-3 py-2">Severidad</th>
              <th class="px-3 py-2">Confianza</th>
              <th class="px-3 py-2">Relevancia</th>
              <th class="px-3 py-2">Eventos</th>
              <th class="px-3 py-2">Evidencia</th>
              <th class="px-3 py-2">URL</th>
            </tr>
          </thead>
          <tbody>
            @for (doc of results(); track $index) {
              <tr class="border-b hover:bg-gray-50">
                <td class="px-3 py-2">{{ $index + 1 }}</td>
                <td class="px-3 py-2" data-field="title">{{ doc.title }}</td>
                <td class="px-3 py-2" data-field="source">{{ doc.source }}</td>
                <td class="px-3 py-2" data-field="date">{{ doc.published_at ?? '—' }}</td>
                <td class="px-3 py-2" data-field="category">{{ doc.category ?? '—' }}</td>
                <td class="px-3 py-2" data-field="severity">
                  <span [class]="severityBadgeClass(doc.severity)"
                    class="inline-block px-2 py-0.5 rounded text-xs font-bold">
                    {{ doc.severity ?? '—' }}
                  </span>
                </td>
                <td class="px-3 py-2" data-field="confidence">
                  @if (doc.confidence != null) {
                    {{ (doc.confidence * 100).toFixed(0) }}%
                  } @else {
                    —
                  }
                </td>
                <td class="px-3 py-2" data-field="relevance">
                  @if (doc.relevance_score != null) {
                    <div class="flex items-center gap-2">
                      <div class="w-20 bg-gray-200 rounded-full h-2">
                        <div class="h-2 rounded-full"
                          [class]="relevanceBarColor(doc.relevance_score)"
                          [style.width.%]="doc.relevance_score">
                        </div>
                      </div>
                      <span class="text-xs text-gray-600">{{ doc.relevance_score }}</span>
                    </div>
                  } @else {
                    —
                  }
                </td>
                <td class="px-3 py-2 max-w-[120px]" data-field="events">
                  @if (doc.events && doc.events.length > 0) {
                    <div class="flex flex-wrap gap-1">
                      @for (ev of doc.events.slice(0, 3); track ev) {
                        <span class="inline-block bg-orange-100 text-orange-800 text-xs px-1.5 py-0.5 rounded">
                          {{ ev }}
                        </span>
                      }
                    </div>
                  } @else {
                    —
                  }
                </td>
                <td class="px-3 py-2 max-w-xs" data-field="evidence">
                  @if (doc.evidence && doc.evidence.length > 0) {
                    <button (click)="toggleEvidence($index)"
                      class="text-blue-500 hover:underline text-xs">
                      {{ expandedRows().has($index) ? 'Ocultar' : 'Ver' }} ({{ doc.evidence.length }})
                    </button>
                    @if (expandedRows().has($index)) {
                      <div class="mt-1 text-xs text-gray-600 space-y-1">
                        @for (ev of doc.evidence.slice(0, 3); track $index) {
                          <p class="border-l-2 border-blue-300 pl-2">{{ ev }}</p>
                        }
                      </div>
                    }
                  } @else {
                    —
                  }
                </td>
                <td class="px-3 py-2" data-field="url">
                  @if (doc.url) {
                    <a [href]="doc.url" target="_blank" rel="noopener noreferrer"
                      class="text-blue-500 hover:underline">Ver</a>
                  } @else {
                    —
                  }
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    }
  `,
})
export class ResultsTableComponent {
  readonly results = input<DocumentResult[]>([]);
  readonly expandedRows = signal<Set<number>>(new Set());

  severityBadgeClass(severity: string | null): string {
    switch (severity) {
      case 'H': return 'bg-red-100 text-red-700';
      case 'M': return 'bg-yellow-100 text-yellow-700';
      case 'L': return 'bg-green-100 text-green-700';
      default: return 'bg-gray-100 text-gray-500';
    }
  }

  relevanceBarColor(score: number): string {
    if (score >= 70) return 'bg-green-500';
    if (score >= 40) return 'bg-yellow-400';
    return 'bg-red-400';
  }

  toggleEvidence(index: number): void {
    const current = new Set(this.expandedRows());
    if (current.has(index)) {
      current.delete(index);
    } else {
      current.add(index);
    }
    this.expandedRows.set(current);
  }
}
