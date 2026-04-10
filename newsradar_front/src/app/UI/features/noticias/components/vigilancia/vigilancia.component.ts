import { Component, inject, OnInit, signal } from '@angular/core';
import { VIGILANCIA_API } from '../../../../../infrastructure/noticias/services/noticias-api.token';
import { TopicItem } from '../../../../../domain/noticias/models';
import { SubscriptionFormComponent } from './subscription-form.component';

@Component({
  selector: 'app-vigilancia',
  standalone: true,
  imports: [SubscriptionFormComponent],
  template: `
    <div class="space-y-5">
      <div class="rounded-2xl border border-dark-border bg-white p-5 shadow-sm">
        <h2 class="text-lg font-semibold text-dark-text">Suscripciones tematicas</h2>
        <p class="mt-2 text-sm leading-6 text-dark-muted">
          Selecciona los temas estrategicos que quieres seguir. En cada tema veras sus subterminos
          principales para entender con claridad el alcance de la vigilancia.
        </p>
      </div>

      <div class="rounded-2xl border border-dark-border bg-white p-5 shadow-sm">
        <h3 class="text-sm font-semibold text-dark-text">Configurar suscripcion</h3>
        <p class="mt-1 text-xs leading-5 text-dark-muted">
          Elige uno o varios temas de interes y registraremos tu correo para futuras entregas.
        </p>

        @if (loading()) {
          <p class="mt-4 text-sm text-dark-muted">Cargando temas...</p>
        } @else if (error()) {
          <div role="alert" class="mt-4 text-sm text-red-600">
            <p>{{ error() }}</p>
            <button (click)="loadTopics()" class="mt-2 text-sm text-blue-500 underline">Reintentar</button>
          </div>
        } @else {
          <div class="mt-4">
            <app-subscription-form
              [topics]="topics()"
              (confirmation)="onSubscriptionCreated($event)"
            />
          </div>
        }

        @if (confirmationMessage()) {
          <div class="mt-4 rounded-xl border border-green-200 bg-green-50 p-3 text-sm text-green-800">
            {{ confirmationMessage() }}
          </div>
        }
      </div>
    </div>
  `,
})
export class VigilanciaComponent implements OnInit {
  private readonly api = inject(VIGILANCIA_API);

  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly topics = signal<TopicItem[]>([]);
  readonly confirmationMessage = signal<string | null>(null);

  ngOnInit(): void {
    this.loadTopics();
  }

  loadTopics(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.fetchTopics().subscribe({
      next: (data) => {
        this.topics.set(data);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(err.message ?? 'No se pudieron cargar los temas disponibles.');
        this.loading.set(false);
      },
    });
  }

  onSubscriptionCreated(message: string): void {
    this.confirmationMessage.set(message);
  }
}
