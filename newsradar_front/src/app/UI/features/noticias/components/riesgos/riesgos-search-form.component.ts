import { Component, Inject, inject, output, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, FormGroup } from '@angular/forms';
import { RIESGOS_API } from '../../../../../infrastructure/noticias/services/noticias-api.token';
import { DocumentResult, RiesgosPreset } from '../../../../../domain/noticias/models';
import { API_BASE_URL } from '../../../../../config/api.token';

const PRESETS: { value: string; label: string }[] = [
  { value: '', label: '— Sin preset —' },
  { value: 'ciber', label: 'Cibernético' },
  { value: 'fraude', label: 'Fraude' },
  { value: 'operacional', label: 'Operacional' },
  { value: 'ambiental_social', label: 'Ambiental / Social' },
  { value: 'all', label: 'Todos' },
];

@Component({
  selector: 'app-riesgos-search-form',
  standalone: true,
  imports: [ReactiveFormsModule],
  template: `
    <form [formGroup]="form" (ngSubmit)="onSubmit()" aria-label="Búsqueda Riesgos Emergentes">
      <fieldset>
        <legend class="text-sm font-semibold mb-3">Parámetros de búsqueda</legend>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="md:col-span-2">
            <label for="riesgos-terms" class="block text-sm mb-1">Términos (separados por coma)</label>
            <input id="riesgos-terms" formControlName="terms"
              class="w-full border rounded px-3 py-2 text-sm" placeholder="ransomware, phishing, breach" />
          </div>
          <div>
            <label for="riesgos-preset" class="block text-sm mb-1">Preset</label>
            <select id="riesgos-preset" formControlName="preset"
              class="w-full border rounded px-3 py-2 text-sm">
              @for (p of presets; track p.value) {
                <option [value]="p.value">{{ p.label }}</option>
              }
            </select>
          </div>
          <div>
            <label for="riesgos-classifier" class="block text-sm mb-1">Clasificador</label>
            <select id="riesgos-classifier" formControlName="classifier"
              class="w-full border rounded px-3 py-2 text-sm">
              <option value="rules">Reglas</option>
              <option value="llm">LLM</option>
            </select>
          </div>
          <div>
            <label for="riesgos-date-from" class="block text-sm mb-1">Desde</label>
            <input id="riesgos-date-from" type="date" formControlName="dateFrom"
              class="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label for="riesgos-date-to" class="block text-sm mb-1">Hasta</label>
            <input id="riesgos-date-to" type="date" formControlName="dateTo"
              class="w-full border rounded px-3 py-2 text-sm" />
          </div>
        </div>
      </fieldset>

      @if (validationError()) {
        <p class="text-red-600 text-sm mt-2" role="alert">{{ validationError() }}</p>
      }

      <div class="flex gap-2 mt-4">
        <button type="submit" [disabled]="loading()"
          class="px-4 py-2 bg-yellow-400 text-black rounded text-sm font-medium disabled:opacity-50">
          @if (loading()) {
            <span class="inline-block animate-spin mr-2">⏳</span> Buscando...
          } @else {
            Buscar
          }
        </button>

        @if (excelUrl()) {
          <button type="button" (click)="downloadExcel()"
            class="px-4 py-2 bg-green-500 text-white rounded text-sm font-medium hover:bg-green-600">
            📥 Exportar Excel
          </button>
        }
      </div>
    </form>
  `,
})
export class RiesgosSearchFormComponent {
  private readonly api = inject(RIESGOS_API);
  private readonly fb = inject(FormBuilder);

  readonly results = output<DocumentResult[]>();
  readonly error = output<string>();
  readonly loadingChange = output<boolean>();
  readonly loading = signal(false);
  readonly validationError = signal<string | null>(null);
  readonly excelUrl = signal<string | null>(null);
  readonly presets = PRESETS;

  constructor(@Inject(API_BASE_URL) private baseUrl: string) {}

  readonly form: FormGroup = this.fb.group({
    terms: [''],
    preset: [''],
    classifier: ['rules'],
    dateFrom: [''],
    dateTo: [''],
  });

  onSubmit(): void {
    this.validationError.set(null);
    this.excelUrl.set(null);
    const v = this.form.value;

    const termsList = (v.terms as string)
      .split(',')
      .map((t: string) => t.trim())
      .filter(Boolean);

    if (termsList.length === 0 && !v.preset) {
      this.validationError.set('Seleccione un preset o ingrese términos de búsqueda.');
      return;
    }

    this.loading.set(true);
    this.loadingChange.emit(true);

    this.api
      .searchRiesgos({
        terms: termsList.length > 0 ? termsList : undefined,
        terms_preset: (v.preset as RiesgosPreset) || undefined,
        date_from: v.dateFrom || undefined,
        date_to: v.dateTo || undefined,
        classifier: v.classifier || undefined,
      })
      .subscribe({
        next: (res) => {
          this.results.emit(res.results);
          if (res.excel_url) {
            this.excelUrl.set(res.excel_url);
          }
          this.loading.set(false);
          this.loadingChange.emit(false);
        },
        error: (err) => {
          this.error.emit(err.message ?? 'Error desconocido');
          this.loading.set(false);
          this.loadingChange.emit(false);
        },
      });
  }

  downloadExcel(): void {
    const url = this.excelUrl();
    if (url) {
      window.open(`${this.baseUrl}${url.replace('/api', '')}`, '_blank');
    }
  }
}
