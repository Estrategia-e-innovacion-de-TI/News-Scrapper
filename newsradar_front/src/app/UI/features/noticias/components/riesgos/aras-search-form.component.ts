import { Component, Inject, inject, output, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, FormGroup } from '@angular/forms';
import { RIESGOS_API } from '../../../../../infrastructure/noticias/services/noticias-api.token';
import { DocumentResult } from '../../../../../domain/noticias/models';
import { API_BASE_URL } from '../../../../../config/api.token';

@Component({
  selector: 'app-aras-search-form',
  standalone: true,
  imports: [ReactiveFormsModule],
  template: `
    <form [formGroup]="form" (ngSubmit)="onSubmit()" aria-label="Busqueda ARAS">
      <fieldset>
        <legend class="mb-3 text-sm font-semibold">Parametros de busqueda ARAS</legend>
        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div class="md:col-span-2">
            <label for="aras-company" class="mb-1 block text-sm">Empresa/Emisor</label>
            <input
              id="aras-company"
              formControlName="company"
              class="w-full rounded-xl border border-dark-border px-3 py-2 text-sm"
              placeholder="Nombre empresarial, razon social o emisor"
            />
          </div>

          <div>
            <label for="aras-nit" class="mb-1 block text-sm">NIT</label>
            <input
              id="aras-nit"
              formControlName="nit"
              class="w-full rounded-xl border border-dark-border px-3 py-2 text-sm"
              placeholder="900123456-7"
            />
          </div>

          <div>
            <label for="aras-risk-category" class="mb-1 block text-sm">Tipo de riesgo</label>
            <select
              id="aras-risk-category"
              formControlName="riskCategory"
              class="w-full rounded-xl border border-dark-border px-3 py-2 text-sm"
            >
              <option value="">Todos</option>
              <option value="lavado_activos">Lavado de activos</option>
              <option value="financiamiento_terrorismo">Financiamiento del terrorismo</option>
              <option value="fraude">Fraude</option>
              <option value="corrupcion">Corrupcion</option>
              <option value="sanciones">Sanciones</option>
              <option value="pep">PEP</option>
              <option value="ambiental">Ambiental</option>
              <option value="social">Social</option>
            </select>
          </div>

          <div>
            <label for="aras-classifier" class="mb-1 block text-sm">Clasificador</label>
            <select
              id="aras-classifier"
              formControlName="classifier"
              class="w-full rounded-xl border border-dark-border px-3 py-2 text-sm"
            >
              <option value="llm">LLM (por defecto)</option>
              <option value="rules">Reglas</option>
            </select>
          </div>

          <div>
            <label for="aras-date-from" class="mb-1 block text-sm">Desde</label>
            <input
              id="aras-date-from"
              type="date"
              formControlName="dateFrom"
              class="w-full rounded-xl border border-dark-border px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label for="aras-date-to" class="mb-1 block text-sm">Hasta</label>
            <input
              id="aras-date-to"
              type="date"
              formControlName="dateTo"
              class="w-full rounded-xl border border-dark-border px-3 py-2 text-sm"
            />
          </div>
        </div>
      </fieldset>

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
export class ArasSearchFormComponent {
  private readonly api = inject(RIESGOS_API);
  private readonly fb = inject(FormBuilder);

  readonly results = output<DocumentResult[]>();
  readonly error = output<string>();
  readonly loadingChange = output<boolean>();
  readonly loading = signal(false);
  readonly excelUrl = signal<string | null>(null);

  constructor(@Inject(API_BASE_URL) private baseUrl: string) {}

  readonly form: FormGroup = this.fb.group({
    company: [''],
    nit: [''],
    riskCategory: [''],
    classifier: ['llm'],
    dateFrom: [''],
    dateTo: [''],
  });

  onSubmit(): void {
    const v = this.form.value;
    this.loading.set(true);
    this.loadingChange.emit(true);
    this.excelUrl.set(null);

    this.api
      .searchAras({
        company: v.company || undefined,
        issuer: v.company || undefined,
        nit: v.nit || undefined,
        risk_category: v.riskCategory || undefined,
        classifier: v.classifier || undefined,
        date_from: v.dateFrom || undefined,
        date_to: v.dateTo || undefined,
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
