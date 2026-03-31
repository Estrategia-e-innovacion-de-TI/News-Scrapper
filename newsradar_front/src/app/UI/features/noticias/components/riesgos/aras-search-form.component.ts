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
    <form [formGroup]="form" (ngSubmit)="onSubmit()" aria-label="Búsqueda ARAS">
      <fieldset>
        <legend class="text-sm font-semibold mb-3">Parámetros de búsqueda ARAS</legend>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label for="aras-company" class="block text-sm mb-1">Empresa</label>
            <input id="aras-company" formControlName="company"
              class="w-full border rounded px-3 py-2 text-sm" placeholder="Nombre de la empresa" />
          </div>
          <div>
            <label for="aras-issuer" class="block text-sm mb-1">Emisor</label>
            <input id="aras-issuer" formControlName="issuer"
              class="w-full border rounded px-3 py-2 text-sm" placeholder="Nombre del emisor" />
          </div>
          <div>
            <label for="aras-nit" class="block text-sm mb-1">NIT</label>
            <input id="aras-nit" formControlName="nit"
              class="w-full border rounded px-3 py-2 text-sm" placeholder="900123456-7" />
          </div>
          <div>
            <label for="aras-risk-category" class="block text-sm mb-1">Tipo de riesgo</label>
            <select id="aras-risk-category" formControlName="riskCategory"
              class="w-full border rounded px-3 py-2 text-sm">
              <option value="">— Todos —</option>
              <option value="lavado_activos">Lavado de activos</option>
              <option value="financiamiento_terrorismo">Financiamiento del terrorismo</option>
              <option value="fraude">Fraude</option>
              <option value="corrupcion">Corrupción</option>
              <option value="sanciones">Sanciones</option>
              <option value="pep">PEP</option>
              <option value="ambiental">Ambiental</option>
              <option value="social">Social</option>
            </select>
          </div>
          <div>
            <label for="aras-classifier" class="block text-sm mb-1">Clasificador</label>
            <select id="aras-classifier" formControlName="classifier"
              class="w-full border rounded px-3 py-2 text-sm">
              <option value="rules">Reglas</option>
              <option value="llm">LLM</option>
            </select>
          </div>
          <div>
            <label for="aras-date-from" class="block text-sm mb-1">Desde</label>
            <input id="aras-date-from" type="date" formControlName="dateFrom"
              class="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label for="aras-date-to" class="block text-sm mb-1">Hasta</label>
            <input id="aras-date-to" type="date" formControlName="dateTo"
              class="w-full border rounded px-3 py-2 text-sm" />
          </div>
        </div>
      </fieldset>

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
    issuer: [''],
    nit: [''],
    riskCategory: [''],
    classifier: ['rules'],
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
        issuer: v.issuer || undefined,
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
