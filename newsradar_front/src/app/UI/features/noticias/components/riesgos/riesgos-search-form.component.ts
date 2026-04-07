import { Component, Inject, inject, output, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, FormGroup } from '@angular/forms';
import { RIESGOS_API } from '../../../../../infrastructure/noticias/services/noticias-api.token';
import { DocumentResult, RiesgosPreset } from '../../../../../domain/noticias/models';
import { API_BASE_URL } from '../../../../../config/api.token';

const PRESETS: { value: string; label: string }[] = [
  { value: '', label: 'Sin preset' },
  { value: 'ciber', label: 'Cibernetico' },
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
    <form [formGroup]="form" (ngSubmit)="onSubmit()" aria-label="Busqueda de riesgos emergentes">
      <fieldset>
        <legend class="mb-3 text-sm font-semibold">Parametros de busqueda</legend>
        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div class="md:col-span-2">
            <label for="riesgos-terms" class="mb-1 block text-sm">Terminos separados por coma</label>
            <input
              id="riesgos-terms"
              formControlName="terms"
              class="w-full rounded-xl border border-dark-border px-3 py-2 text-sm"
              placeholder="ransomware, phishing, breach"
            />
          </div>

          <div>
            <label for="riesgos-preset" class="mb-1 block text-sm">Preset</label>
            <select
              id="riesgos-preset"
              formControlName="preset"
              class="w-full rounded-xl border border-dark-border px-3 py-2 text-sm"
            >
              @for (p of presets; track p.value) {
                <option [value]="p.value">{{ p.label }}</option>
              }
            </select>
          </div>

          <div>
            <label for="riesgos-classifier" class="mb-1 block text-sm">Clasificador</label>
            <select
              id="riesgos-classifier"
              formControlName="classifier"
              class="w-full rounded-xl border border-dark-border px-3 py-2 text-sm"
            >
              <option value="llm">LLM (por defecto)</option>
              <option value="rules">Reglas</option>
            </select>
          </div>

          <div>
            <label for="riesgos-date-from" class="mb-1 block text-sm">Desde</label>
            <input
              id="riesgos-date-from"
              type="date"
              formControlName="dateFrom"
              class="w-full rounded-xl border border-dark-border px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label for="riesgos-date-to" class="mb-1 block text-sm">Hasta</label>
            <input
              id="riesgos-date-to"
              type="date"
              formControlName="dateTo"
              class="w-full rounded-xl border border-dark-border px-3 py-2 text-sm"
            />
          </div>
        </div>
      </fieldset>

      @if (validationError()) {
        <p class="mt-2 text-sm text-red-700" role="alert">{{ validationError() }}</p>
      }

      <div class="mt-4 flex gap-2">
        <button
          type="submit"
          [disabled]="loading()"
          class="rounded-xl bg-yellow-300 px-4 py-2 text-sm font-semibold text-dark-text shadow-sm disabled:opacity-50"
        >
          @if (loading()) {
            Buscando...
          } @else {
            Buscar
          }
        </button>

        @if (excelUrl()) {
          <button
            type="button"
            (click)="downloadExcel()"
            class="rounded-xl bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-700"
          >
            Exportar Excel
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
    classifier: ['llm'],
    dateFrom: [''],
    dateTo: [''],
  });

  onSubmit(): void {
    this.validationError.set(null);
    this.excelUrl.set(null);
    const v = this.form.value;

    const termsList = (v.terms as string)
      .split(',')
      .map((term: string) => term.trim())
      .filter(Boolean);

    if (termsList.length === 0 && !v.preset) {
      this.validationError.set('Seleccione un preset o ingrese terminos de busqueda.');
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
