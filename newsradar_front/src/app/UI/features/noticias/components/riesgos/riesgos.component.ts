import { Component, signal } from '@angular/core';
import { ArasSearchFormComponent } from './aras-search-form.component';
import { RiesgosSearchFormComponent } from './riesgos-search-form.component';
import { ResultsTableComponent } from './results-table.component';
import { DocumentResult } from '../../../../../domain/noticias/models';

@Component({
  selector: 'app-riesgos',
  standalone: true,
  imports: [ArasSearchFormComponent, RiesgosSearchFormComponent, ResultsTableComponent],
  template: `
    <div class="space-y-6" data-testid="content-riesgos">
      <h2 class="text-lg font-semibold">ARAS / Riesgos</h2>
      <p class="text-sm text-gray-500">
        Consulta por empresa, emisor o NIT, y tambien por terminos generales de riesgo desde la misma vista.
      </p>

      <div class="flex gap-2 border-b border-gray-200 mb-4" role="tablist" aria-label="Sub-secciones de Riesgos">
        <button
          role="tab"
          [attr.aria-selected]="activeSubTab() === 'aras'"
          class="px-3 py-1.5 text-sm rounded-t"
          [class.bg-yellow-400]="activeSubTab() === 'aras'"
          [class.font-semibold]="activeSubTab() === 'aras'"
          [class.text-gray-600]="activeSubTab() !== 'aras'"
          (click)="activeSubTab.set('aras')"
        >
          Empresa / emisor
        </button>
        <button
          role="tab"
          [attr.aria-selected]="activeSubTab() === 'riesgos'"
          class="px-3 py-1.5 text-sm rounded-t"
          [class.bg-yellow-400]="activeSubTab() === 'riesgos'"
          [class.font-semibold]="activeSubTab() === 'riesgos'"
          [class.text-gray-600]="activeSubTab() !== 'riesgos'"
          (click)="activeSubTab.set('riesgos')"
        >
          Terminos de riesgo
        </button>
      </div>

      @if (activeSubTab() === 'aras') {
        <app-aras-search-form
          (results)="onResults($event)"
          (error)="onError($event)"
          (loadingChange)="arasLoading.set($event)"
        />
      }

      @if (activeSubTab() === 'riesgos') {
        <app-riesgos-search-form
          (results)="onResults($event)"
          (error)="onError($event)"
          (loadingChange)="riesgosLoading.set($event)"
        />
      }

      @if (error()) {
        <p class="text-red-600 text-sm" role="alert">{{ error() }}</p>
      }

      <app-results-table [results]="results()" />
    </div>
  `,
})
export class RiesgosComponent {
  readonly activeSubTab = signal<'aras' | 'riesgos'>('aras');
  readonly arasLoading = signal(false);
  readonly riesgosLoading = signal(false);
  readonly error = signal<string | null>(null);
  readonly results = signal<DocumentResult[]>([]);

  onResults(data: DocumentResult[]): void {
    this.error.set(null);
    this.results.set(data);
  }

  onError(message: string): void {
    this.error.set(message);
  }
}
