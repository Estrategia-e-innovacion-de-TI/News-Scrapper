import { Component, Inject, OnInit, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { API_BASE_URL } from '../../../../../config/api.token';

interface ExecutionView {
  id: string;
  run_key: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  metrics: Record<string, unknown>;
}

interface DocumentView {
  id: string;
  title: string;
  source_id: string;
  source_type: string | null;
  published_at: string | null;
  relevance_score: number | null;
  category: string | null;
  url: string;
}

interface TopicView {
  group_id: string;
  display_name: string;
  term_count: number;
}

@Component({
  selector: 'app-tech-watch',
  standalone: true,
  template: `
    <div class="space-y-6">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h2 class="text-lg font-semibold">Administracion de ingesta</h2>
          <p class="text-sm text-gray-500">
            Estado de ejecuciones, documentos guardados con relevancia mayor a 40, topicos disponibles y resumen analitico.
          </p>
        </div>
        <button
          (click)="runTechWatch()"
          class="px-4 py-2 bg-yellow-400 text-black rounded text-sm font-medium disabled:opacity-50"
          [disabled]="running()"
        >
          @if (running()) { Ejecutando... } @else { Ejecutar flujo }
        </button>
      </div>

      @if (error()) {
        <p class="text-red-600 text-sm" role="alert">{{ error() }}</p>
      }

      <div class="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <section class="border rounded p-4 bg-white">
          <h3 class="font-medium mb-3">Ejecuciones</h3>
          @if (loading()) {
            <p class="text-sm text-gray-500">Cargando...</p>
          } @else if (executions().length === 0) {
            <p class="text-sm text-gray-400">Sin ejecuciones registradas.</p>
          } @else {
            <div class="space-y-3">
              @for (execution of executions(); track execution.id) {
                <div class="border rounded p-3 text-sm">
                  <div class="flex items-center justify-between">
                    <span class="font-medium">{{ execution.run_key }}</span>
                    <span class="text-xs uppercase text-gray-500">{{ execution.status }}</span>
                  </div>
                  <p class="text-gray-500 mt-1">{{ execution.started_at }}</p>
                </div>
              }
            </div>
          }
        </section>

        <section class="border rounded p-4 bg-white">
          <h3 class="font-medium mb-3">Topicos</h3>
          @if (topics().length === 0) {
            <p class="text-sm text-gray-400">Sin topicos cargados.</p>
          } @else {
            <div class="flex flex-wrap gap-2">
              @for (topic of topics(); track topic.group_id) {
                <span class="px-3 py-1 rounded-full bg-gray-100 text-sm">
                  {{ topic.display_name }} ({{ topic.term_count }})
                </span>
              }
            </div>
          }
        </section>

        <section class="border rounded p-4 bg-white">
          <h3 class="font-medium mb-3">Snapshot actual</h3>
          @if (snapshotStatus()) {
            <p class="text-sm">{{ snapshotStatus() }}</p>
          } @else {
            <p class="text-sm text-gray-400">Mapa de tendencias aun no generado.</p>
          }
        </section>
      </div>

      <section class="border rounded p-4 bg-white">
        <h3 class="font-medium mb-3">Documentos recientes</h3>
        @if (documents().length === 0) {
          <p class="text-sm text-gray-400">Sin documentos persistidos.</p>
        } @else {
          <div class="space-y-2">
            @for (doc of documents(); track doc.id) {
              <a [href]="doc.url" target="_blank" class="block border rounded p-3 hover:bg-gray-50">
                <div class="flex items-center justify-between gap-3">
                  <span class="font-medium text-sm">{{ doc.title }}</span>
                  <span class="text-xs text-gray-500">{{ doc.relevance_score ?? 'sin dato' }}</span>
                </div>
                <p class="text-xs text-gray-500 mt-1">{{ doc.source_id }} · {{ doc.published_at || 'sin fecha' }}</p>
              </a>
            }
          </div>
        }
      </section>
    </div>
  `,
})
export class TechWatchComponent implements OnInit {
  private readonly http = inject(HttpClient);

  readonly loading = signal(false);
  readonly running = signal(false);
  readonly error = signal<string | null>(null);
  readonly executions = signal<ExecutionView[]>([]);
  readonly documents = signal<DocumentView[]>([]);
  readonly topics = signal<TopicView[]>([]);
  readonly snapshotStatus = signal<string | null>(null);

  constructor(@Inject(API_BASE_URL) private baseUrl: string) {}

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.loading.set(true);
    this.http.get<ExecutionView[]>(`${this.baseUrl}/tech-watch/executions`).subscribe({
      next: (executions) => {
        this.executions.set(executions);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('No se pudieron cargar las ejecuciones.');
        this.loading.set(false);
      },
    });
    this.http.get<DocumentView[]>(`${this.baseUrl}/tech-watch/documents?limit=20&min_relevance_score=40`).subscribe({
      next: (documents) => this.documents.set(documents),
      error: () => this.documents.set([]),
    });
    this.http.get<TopicView[]>(`${this.baseUrl}/tech-watch/topics`).subscribe({
      next: (topics) => this.topics.set(topics),
      error: () => this.topics.set([]),
    });
    this.http.get<any>(`${this.baseUrl}/trendmap/latest`).subscribe({
      next: (snapshot) => this.snapshotStatus.set(`Resumen generado: ${snapshot.generated_at || snapshot.snapshot_id}`),
      error: () => this.snapshotStatus.set(null),
    });
  }

  runTechWatch(): void {
    this.running.set(true);
    this.http.post<{ run_id: string }>(`${this.baseUrl}/tech-watch/run`, {}).subscribe({
      next: (response) => {
        this.snapshotStatus.set(`Ejecucion iniciada: ${response.run_id}`);
        this.running.set(false);
        this.refresh();
      },
      error: () => {
        this.error.set('No se pudo iniciar el flujo de vigilancia.');
        this.running.set(false);
      },
    });
  }
}
