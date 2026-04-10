import { Component, inject, input, output, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, FormGroup, FormArray, Validators } from '@angular/forms';
import { VIGILANCIA_API } from '../../../../../infrastructure/noticias/services/noticias-api.token';
import { TopicItem } from '../../../../../domain/noticias/models';

@Component({
  selector: 'app-subscription-form',
  standalone: true,
  imports: [ReactiveFormsModule],
  template: `
    <form [formGroup]="form" (ngSubmit)="onSubmit()" aria-label="Suscripción a vigilancia tecnológica">
      <fieldset>
        <legend class="mb-3 text-sm font-semibold text-dark-text">Datos del suscriptor</legend>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label for="vigilancia-email" class="mb-1 block text-sm text-dark-text">Correo</label>
            <input id="vigilancia-email" type="email" formControlName="email"
              class="w-full rounded-xl border border-dark-border px-3 py-2 text-sm" placeholder="usuario&#64;empresa.com" />
            @if (form.get('email')?.touched && form.get('email')?.invalid) {
              <p class="text-red-500 text-xs mt-1">Ingrese un email válido.</p>
            }
          </div>
          <div>
            <label for="vigilancia-name" class="mb-1 block text-sm text-dark-text">Nombre</label>
            <input id="vigilancia-name" formControlName="name"
              class="w-full rounded-xl border border-dark-border px-3 py-2 text-sm" placeholder="Nombre completo" />
            @if (form.get('name')?.touched && form.get('name')?.invalid) {
              <p class="text-red-500 text-xs mt-1">El nombre es obligatorio.</p>
            }
          </div>
        </div>
      </fieldset>

      <fieldset class="mt-4">
        <legend class="mb-3 text-sm font-semibold text-dark-text">Temas de interes</legend>
        <p class="mb-3 text-xs leading-5 text-dark-muted">
          Cada tema incluye los subterminos principales que se usan para construir la vigilancia.
        </p>
        <div formArrayName="selectedGroups" class="space-y-3">
          @for (topic of topics(); track topic.group_id; let i = $index) {
            <label class="block cursor-pointer rounded-2xl border border-dark-border bg-white p-4 transition hover:border-yellow-400 hover:bg-yellow-50">
              <div class="flex items-start gap-3">
                <input class="mt-1" type="checkbox" [formControlName]="i" />
                <div class="min-w-0 flex-1">
                  <div class="flex flex-wrap items-center gap-2">
                    <span class="text-sm font-semibold text-dark-text">{{ topic.display_name }}</span>
                    <span class="rounded-full border border-dark-border bg-dark-bg px-2 py-0.5 text-[11px] text-dark-muted">
                      {{ topic.term_count }} subterminos
                    </span>
                  </div>
                  @if ((topic.terms?.length ?? 0) > 0) {
                    <div class="mt-3 flex flex-wrap gap-2">
                      @for (term of (topic.terms ?? []); track term) {
                        <span class="rounded-full border border-dark-border bg-dark-surface px-2 py-1 text-[11px] leading-4 text-dark-muted">
                          {{ term }}
                        </span>
                      }
                    </div>
                  }
                </div>
              </div>
            </label>
          }
        </div>
        @if (showGroupsError()) {
          <p class="text-red-500 text-xs mt-1">Seleccione al menos un tema.</p>
        }
      </fieldset>

      @if (error()) {
        <p class="text-red-600 text-sm mt-2" role="alert">{{ error() }}</p>
      }

      <button type="submit" [disabled]="loading()"
        class="mt-4 rounded-full bg-yellow-400 px-4 py-2 text-sm font-medium text-black disabled:opacity-50">
        @if (loading()) {
          Suscribiendo...
        } @else {
          Suscribirse
        }
      </button>
    </form>
  `,
})
export class SubscriptionFormComponent {
  private readonly api = inject(VIGILANCIA_API);
  private readonly fb = inject(FormBuilder);

  readonly topics = input<TopicItem[]>([]);
  readonly confirmation = output<string>();
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly showGroupsError = signal(false);

  readonly form: FormGroup = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    name: ['', Validators.required],
    selectedGroups: this.fb.array([]),
  });

  get groupsArray(): FormArray {
    return this.form.get('selectedGroups') as FormArray;
  }

  ngOnChanges(): void {
    const arr = this.groupsArray;
    arr.clear();
    for (const _ of this.topics()) {
      arr.push(this.fb.control(false));
    }
  }

  onSubmit(): void {
    this.form.markAllAsTouched();
    this.error.set(null);
    this.showGroupsError.set(false);

    const selectedIds = this.topics()
      .filter((_, i) => this.groupsArray.at(i).value)
      .map((t) => t.group_id);

    if (selectedIds.length === 0) {
      this.showGroupsError.set(true);
      return;
    }

    if (this.form.invalid) return;

    this.loading.set(true);

    this.api
      .subscribe({
        email: this.form.value.email,
        name: this.form.value.name,
        query_groups: selectedIds,
      })
      .subscribe({
        next: (res) => {
          this.confirmation.emit(
            `Suscripción exitosa para ${res.email}. Temas suscritos: ${res.subscribed_groups.join(', ')}`
          );
          this.loading.set(false);
        },
        error: (err) => {
          this.error.set(err.message ?? 'Error desconocido');
          this.loading.set(false);
        },
      });
  }
}
