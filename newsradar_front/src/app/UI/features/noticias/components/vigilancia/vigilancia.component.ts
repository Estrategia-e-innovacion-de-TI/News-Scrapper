import { Component, inject, OnInit, signal } from '@angular/core';
import { VIGILANCIA_API } from '../../../../../infrastructure/noticias/services/noticias-api.token';
import {
  Subscription,
  SubscriptionDelivery,
  TopicItem,
} from '../../../../../domain/noticias/models';
import { SubscriptionFormComponent } from './subscription-form.component';

@Component({
  selector: 'app-vigilancia',
  standalone: true,
  imports: [SubscriptionFormComponent],
  template: `
    <div class="space-y-4">
      <h2 class="text-lg font-semibold">Subscripciones</h2>
      <p class="text-sm text-gray-500">
        Gestiona el boletin de tendencias y consulta el historial de entregas procesadas en backend.
      </p>

      @if (loading()) {
        <p class="text-gray-500 text-sm">Cargando temas...</p>
      } @else if (error()) {
        <div role="alert" class="text-red-600 text-sm">
          <p>{{ error() }}</p>
          <button (click)="loadTopics()" class="mt-2 text-blue-500 underline text-sm">Reintentar</button>
        </div>
      } @else {
        <app-subscription-form
          [topics]="topics()"
          (confirmation)="onSubscriptionCreated($event)"
        />
      }

      @if (confirmationMessage()) {
        <div class="bg-green-50 border border-green-200 rounded p-3 text-sm text-green-800">
          {{ confirmationMessage() }}
        </div>
      }

      <div class="mt-6">
        <h3 class="text-md font-semibold mb-2">Suscripciones activas</h3>
        @if (subsLoading()) {
          <p class="text-gray-500 text-sm">Cargando suscripciones...</p>
        } @else if (subscriptions().length === 0) {
          <p class="text-gray-400 text-sm">No hay suscripciones activas.</p>
        } @else {
          <div class="space-y-2">
            @for (sub of subscriptions(); track sub.id) {
              <div class="flex items-center justify-between border rounded p-3 text-sm">
                <div>
                  <span class="font-medium">{{ sub.email }}</span>
                  <span class="text-gray-500 ml-2">· {{ sub.query_groups.join(', ') }}</span>
                </div>
                <button
                  (click)="deleteSub(sub.id)"
                  class="text-red-500 hover:text-red-700 text-xs font-medium"
                  [disabled]="deletingId() === sub.id"
                >
                  @if (deletingId() === sub.id) {
                    Eliminando...
                  } @else {
                    Eliminar
                  }
                </button>
              </div>
            }
          </div>
        }
      </div>

      <div class="mt-6">
        <h3 class="text-md font-semibold mb-2">Historial de entregas</h3>
        @if (deliveriesLoading()) {
          <p class="text-gray-500 text-sm">Cargando entregas...</p>
        } @else if (deliveries().length === 0) {
          <p class="text-gray-400 text-sm">Aun no hay entregas registradas.</p>
        } @else {
          <div class="space-y-2">
            @for (delivery of deliveries(); track delivery.id) {
              <div class="border rounded p-3 text-sm">
                <div class="flex items-center justify-between gap-3">
                  <span class="font-medium">{{ delivery.subject || 'Entrega sin asunto' }}</span>
                  <span class="text-xs uppercase text-gray-500">{{ delivery.status }}</span>
                </div>
                <p class="text-gray-500 mt-1">
                  Subscription: {{ delivery.subscription_id }} · {{ delivery.delivered_at || 'Pendiente' }}
                </p>
              </div>
            }
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
  readonly subscriptions = signal<Subscription[]>([]);
  readonly subsLoading = signal(false);
  readonly deletingId = signal<string | null>(null);
  readonly deliveries = signal<SubscriptionDelivery[]>([]);
  readonly deliveriesLoading = signal(false);

  ngOnInit(): void {
    this.loadTopics();
    this.loadSubscriptions();
    this.loadDeliveries();
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

  loadSubscriptions(): void {
    this.subsLoading.set(true);
    this.api.listSubscriptions().subscribe({
      next: (subs) => {
        this.subscriptions.set(subs);
        this.subsLoading.set(false);
      },
      error: () => this.subsLoading.set(false),
    });
  }

  loadDeliveries(): void {
    this.deliveriesLoading.set(true);
    this.api.listDeliveries().subscribe({
      next: (deliveries) => {
        this.deliveries.set(deliveries);
        this.deliveriesLoading.set(false);
      },
      error: () => this.deliveriesLoading.set(false),
    });
  }

  onSubscriptionCreated(message: string): void {
    this.confirmationMessage.set(message);
    this.loadSubscriptions();
    this.loadDeliveries();
  }

  deleteSub(id: string): void {
    this.deletingId.set(id);
    this.api.deleteSubscription(id).subscribe({
      next: () => {
        this.subscriptions.update((subs) => subs.filter((s) => s.id !== id));
        this.deletingId.set(null);
      },
      error: () => this.deletingId.set(null),
    });
  }
}
