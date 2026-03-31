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
        <legend class="text-sm font-semibold mb-3">Datos del suscriptor</legend>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label for="vigilancia-email" class="block text-sm mb-1">Email</label>
            <input id="vigilancia-email" type="email" formControlName="email"
              class="w-full border rounded px-3 py-2 text-sm" placeholder="usuario&#64;empresa.com" />
            @if (form.get('email')?.touched && form.get('email')?.invalid) {
              <p class="text-red-500 text-xs mt-1">Ingrese un email válido.</p>
            }
          </div>
          <div>
            <label for="vigilancia-name" class="block text-sm mb-1">Nombre</label>
            <input id="vigilancia-name" formControlName="name"
              class="w-full border rounded px-3 py-2 text-sm" placeholder="Nombre completo" />
            @if (form.get('name')?.touched && form.get('name')?.invalid) {
              <p class="text-red-500 text-xs mt-1">El nombre es obligatorio.</p>
            }
          </div>
        </div>
      </fieldset>

      <fieldset class="mt-4">
        <legend class="text-sm font-semibold mb-3">Temas de interés</legend>
        <div formArrayName="selectedGroups" class="space-y-1">
          @for (topic of topics(); track topic.group_id; let i = $index) {
            <label class="flex items-center gap-2 text-sm">
              <input type="checkbox" [formControlName]="i" />
              {{ topic.display_name }} ({{ topic.term_count }} términos)
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
        class="mt-4 px-4 py-2 bg-yellow-400 text-black rounded text-sm font-medium disabled:opacity-50">
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
