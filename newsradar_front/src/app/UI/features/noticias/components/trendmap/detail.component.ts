import { Component, input, signal, computed } from '@angular/core';
import { TrendmapArticle } from '../../../../../domain/noticias/models';

type SortField = 'title' | 'source' | 'date' | 'score';
type SortDir = 'asc' | 'desc';

@Component({
  selector: 'app-trendmap-detail',
  standalone: true,
  template: `
    <div class="bg-dark-surface border border-dark-border rounded-lg p-4">
      <div class="flex justify-between items-center mb-4">
        <h4 class="text-sm font-semibold text-dark-text">
          Artículos ({{ sortedArticles().length }})
        </h4>
      </div>

      @if (sortedArticles().length === 0) {
        <p class="text-dark-muted text-sm">No hay artículos para mostrar.</p>
      } @else {
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-dark-border">
                <th class="text-left py-2 px-3 text-dark-muted font-medium cursor-pointer hover:text-dark-text"
                    (click)="toggleSort('title')">
                  Título {{ sortIndicator('title') }}
                </th>
                <th class="text-left py-2 px-3 text-dark-muted font-medium cursor-pointer hover:text-dark-text"
                    (click)="toggleSort('source')">
                  Fuente {{ sortIndicator('source') }}
                </th>
                <th class="text-left py-2 px-3 text-dark-muted font-medium cursor-pointer hover:text-dark-text"
                    (click)="toggleSort('date')">
                  Fecha {{ sortIndicator('date') }}
                </th>
                <th class="text-left py-2 px-3 text-dark-muted font-medium cursor-pointer hover:text-dark-text"
                    (click)="toggleSort('score')">
                  Score {{ sortIndicator('score') }}
                </th>
                <th class="text-left py-2 px-3 text-dark-muted font-medium">Enlace</th>
              </tr>
            </thead>
            <tbody>
              @for (article of sortedArticles(); track article.id) {
                <tr class="border-b border-dark-border/50 hover:bg-dark-bg/50 transition-colors">
                  <td class="py-2 px-3 text-dark-text max-w-xs truncate">{{ article.title }}</td>
                  <td class="py-2 px-3 text-dark-muted">{{ article.source }}</td>
                  <td class="py-2 px-3 text-dark-muted whitespace-nowrap">{{ article.date }}</td>
                  <td class="py-2 px-3">
                    <span class="inline-flex items-center gap-1">
                      <span class="w-12 h-1.5 rounded-full bg-dark-border overflow-hidden inline-block">
                        <span class="h-full rounded-full bg-dark-accent block"
                              [style.width.%]="article.score"></span>
                      </span>
                      <span class="text-dark-muted text-xs">{{ article.score | number:'1.0-0' }}</span>
                    </span>
                  </td>
                  <td class="py-2 px-3">
                    <a [href]="article.url" target="_blank" rel="noopener noreferrer"
                       class="text-dark-accent hover:underline text-xs">
                      Abrir ↗
                    </a>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    </div>
  `,
  imports: [],
})
export class TrendmapDetailComponent {
  readonly articles = input<TrendmapArticle[]>([]);

  readonly sortField = signal<SortField>('score');
  readonly sortDir = signal<SortDir>('desc');

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
          cmp = a.date.localeCompare(b.date);
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
    return this.sortDir() === 'asc' ? '↑' : '↓';
  }
}
