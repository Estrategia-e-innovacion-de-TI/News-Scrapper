import { Component, Inject, OnInit, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { API_BASE_URL } from '../../../../../config/api.token';

interface RiskmapSnapshot {
  snapshot_id: string;
  generated_at: string;
  summary: {
    total_documents: number;
    total_clusters: number;
    dominant_risks: string[];
  };
  clusters: Array<{
    cluster_id: string;
    label: string;
    dominant_risk: string;
    documents: number;
    avg_score: number;
  }>;
  top_documents: Array<{
    id: string;
    title: string;
    source: string;
    score: number;
    summary: string;
  }>;
}

@Component({
  selector: 'app-riskmap',
  standalone: true,
  template: `
    <div class="space-y-6">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h2 class="text-lg font-semibold">Risk Mapping</h2>
          <p class="text-sm text-gray-500">
            Visualiza el snapshot persistido del analisis de riesgos sin recalculo en frontend.
          </p>
        </div>
        <button
          (click)="runRiskmap()"
          class="px-4 py-2 bg-yellow-400 text-black rounded text-sm font-medium disabled:opacity-50"
          [disabled]="running()"
        >
          @if (running()) { Ejecutando... } @else { Ejecutar risk mapping }
        </button>
      </div>

      @if (error()) {
        <p class="text-red-600 text-sm">{{ error() }}</p>
      }

      @if (snapshot()) {
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="border rounded p-4 bg-white">
            <p class="text-sm text-gray-500">Documentos</p>
            <p class="text-2xl font-semibold">{{ snapshot()!.summary.total_documents }}</p>
          </div>
          <div class="border rounded p-4 bg-white">
            <p class="text-sm text-gray-500">Clusters</p>
            <p class="text-2xl font-semibold">{{ snapshot()!.summary.total_clusters }}</p>
          </div>
          <div class="border rounded p-4 bg-white">
            <p class="text-sm text-gray-500">Generado</p>
            <p class="text-sm font-medium">{{ snapshot()!.generated_at }}</p>
          </div>
        </div>

        <section class="border rounded p-4 bg-white">
          <h3 class="font-medium mb-3">Riesgos dominantes</h3>
          <div class="flex flex-wrap gap-2">
            @for (risk of snapshot()!.summary.dominant_risks; track risk) {
              <span class="px-3 py-1 rounded-full bg-gray-100 text-sm">{{ risk }}</span>
            }
          </div>
        </section>

        <section class="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <div class="border rounded p-4 bg-white">
            <h3 class="font-medium mb-3">Clusters</h3>
            <div class="space-y-2">
              @for (cluster of snapshot()!.clusters; track cluster.cluster_id) {
                <div class="border rounded p-3 text-sm">
                  <div class="flex items-center justify-between gap-3">
                    <span class="font-medium">{{ cluster.label }}</span>
                    <span class="text-xs text-gray-500">{{ cluster.documents }} docs</span>
                  </div>
                  <p class="text-gray-500 mt-1">{{ cluster.dominant_risk }} · score {{ cluster.avg_score }}</p>
                </div>
              }
            </div>
          </div>

          <div class="border rounded p-4 bg-white">
            <h3 class="font-medium mb-3">Top documentos</h3>
            <div class="space-y-2">
              @for (doc of snapshot()!.top_documents; track doc.id) {
                <div class="border rounded p-3 text-sm">
                  <div class="flex items-center justify-between gap-3">
                    <span class="font-medium">{{ doc.title }}</span>
                    <span class="text-xs text-gray-500">{{ doc.score }}</span>
                  </div>
                  <p class="text-gray-500 mt-1">{{ doc.source }}</p>
                </div>
              }
            </div>
          </div>
        </section>
      } @else {
        <p class="text-sm text-gray-400">No hay snapshot de risk mapping disponible.</p>
      }
    </div>
  `,
})
export class RiskmapComponent implements OnInit {
  private readonly http = inject(HttpClient);

  readonly snapshot = signal<RiskmapSnapshot | null>(null);
  readonly error = signal<string | null>(null);
  readonly running = signal(false);

  constructor(@Inject(API_BASE_URL) private baseUrl: string) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.http.get<RiskmapSnapshot>(`${this.baseUrl}/riskmap/latest`).subscribe({
      next: (snapshot) => this.snapshot.set(snapshot),
      error: () => this.snapshot.set(null),
    });
  }

  runRiskmap(): void {
    this.running.set(true);
    this.http.post<{ run_id: string }>(`${this.baseUrl}/riskmap/run`, {}).subscribe({
      next: () => {
        this.running.set(false);
        this.load();
      },
      error: () => {
        this.error.set('No se pudo iniciar el risk mapping.');
        this.running.set(false);
      },
    });
  }
}
