import { DecimalPipe } from '@angular/common';
import { Component, computed, input, output } from '@angular/core';
import {
  FiltersMetadata,
  LifecycleStage,
  QualityChecks,
  TrendmapCluster,
} from '../../../../../domain/noticias/models';

type ClusterSort = 'impact' | 'momentum' | 'novelty' | 'size' | 'quality' | 'maturity';

interface SortOption {
  value: ClusterSort;
  label: string;
}

const SORT_OPTIONS: SortOption[] = [
  { value: 'impact', label: 'Impacto' },
  { value: 'momentum', label: 'Momentum' },
  { value: 'novelty', label: 'Novedad' },
  { value: 'size', label: 'Tamano cluster' },
  { value: 'quality', label: 'Calidad analitica' },
  { value: 'maturity', label: 'Madurez' },
];

@Component({
  selector: 'app-trendmap-sidebar',
  standalone: true,
  imports: [DecimalPipe],
  template: `
    <aside class="w-full shrink-0 space-y-4 2xl:w-80">
      <section class="rounded-2xl border border-dark-border bg-dark-surface p-4">
        <div class="flex items-center justify-between gap-3">
          <div>
            <h4 class="text-sm font-semibold text-dark-text">Filtros</h4>
            <p class="mt-1 text-xs leading-5 text-dark-muted">
              Ajusta lectura ejecutiva y priorizacion del mapa.
            </p>
          </div>
          <button
            class="rounded-full border border-dark-border bg-dark-bg px-3 py-1 text-[11px] text-dark-muted transition hover:text-dark-text"
            type="button"
            (click)="clearRequested.emit()"
          >
            Limpiar
          </button>
        </div>

        <div class="mt-4 grid gap-3">
          <label class="grid gap-1">
            <span class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">
              Categoria
            </span>
            <select
              class="rounded-xl border border-dark-border bg-dark-bg px-3 py-2 text-sm text-dark-text"
              [value]="filterCategory() ?? ''"
              (change)="onCategoryChange($event)"
            >
              <option value="">Todas</option>
              @for (item of categoriesList(); track item) {
                <option [value]="item">{{ item }}</option>
              }
            </select>
          </label>

          @if (visibleCategories().length > 0) {
            <div class="rounded-xl border border-dark-border bg-dark-bg/60 p-3">
              <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">
                Categorias visibles
              </p>
              <div class="mt-3 flex flex-wrap gap-2">
                @for (item of visibleCategories(); track item) {
                  <button
                    class="inline-flex items-center gap-2 rounded-full border border-dark-border bg-dark-surface px-3 py-1 text-xs text-dark-text transition hover:border-dark-muted"
                    type="button"
                    (click)="categoryChanged.emit(item === filterCategory() ? null : item)"
                  >
                    <span
                      class="h-2.5 w-2.5 rounded-full"
                      [style.backgroundColor]="categoryColor(item)"
                    ></span>
                    {{ item }}
                  </button>
                }
              </div>
            </div>
          }

          <label class="grid gap-1">
            <span class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">
              Tipo de fuente
            </span>
            <select
              class="rounded-xl border border-dark-border bg-dark-bg px-3 py-2 text-sm text-dark-text"
              [value]="filterSourceType() ?? ''"
              (change)="onSourceTypeChange($event)"
            >
              <option value="">Todas</option>
              @for (item of sourceTypes(); track item) {
                <option [value]="item">{{ item }}</option>
              }
            </select>
          </label>

          <label class="grid gap-1">
            <span class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">
              Madurez
            </span>
            <select
              class="rounded-xl border border-dark-border bg-dark-bg px-3 py-2 text-sm text-dark-text"
              [value]="filterMaturityStage() ?? ''"
              (change)="onMaturityStageChange($event)"
            >
              <option value="">Todas</option>
              @for (item of maturityStages(); track item) {
                <option [value]="item">{{ formatStage(item) }}</option>
              }
            </select>
          </label>

          <label class="grid gap-1">
            <span class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">
              Hype stage
            </span>
            <select
              class="rounded-xl border border-dark-border bg-dark-bg px-3 py-2 text-sm text-dark-text"
              [value]="filterHypeStage() ?? ''"
              (change)="onHypeStageChange($event)"
            >
              <option value="">Todas</option>
              @for (item of hypeStages(); track item) {
                <option [value]="item">{{ formatStage(item) }}</option>
              }
            </select>
          </label>

          <label class="grid gap-1">
            <span class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">
              Impacto
            </span>
            <select
              class="rounded-xl border border-dark-border bg-dark-bg px-3 py-2 text-sm text-dark-text"
              [value]="filterImpactBand() ?? ''"
              (change)="onImpactBandChange($event)"
            >
              <option value="">Todos</option>
              @for (item of impactBands; track item.value) {
                <option [value]="item.value">{{ item.label }}</option>
              }
            </select>
          </label>

          <label class="grid gap-1">
            <span class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">
              Estado de senal
            </span>
            <select
              class="rounded-xl border border-dark-border bg-dark-bg px-3 py-2 text-sm text-dark-text"
              [value]="filterSignalState() ?? ''"
              (change)="onSignalStateChange($event)"
            >
              <option value="">Todos</option>
              @for (item of signalStates(); track item) {
                <option [value]="item">{{ item }}</option>
              }
            </select>
          </label>

          <label class="grid gap-1">
            <span class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">
              Comparativo
            </span>
            <select
              class="rounded-xl border border-dark-border bg-dark-bg px-3 py-2 text-sm text-dark-text"
              [value]="filterComparativeStatus() ?? ''"
              (change)="onComparativeStatusChange($event)"
            >
              <option value="">Todos</option>
              @for (item of comparativeStatuses(); track item) {
                <option [value]="item">{{ item }}</option>
              }
            </select>
          </label>

          <label class="grid gap-1">
            <span class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">
              Banda de novedad
            </span>
            <select
              class="rounded-xl border border-dark-border bg-dark-bg px-3 py-2 text-sm text-dark-text"
              [value]="filterNoveltyBand() ?? ''"
              (change)="onNoveltyBandChange($event)"
            >
              <option value="">Todas</option>
              @for (item of noveltyBands(); track item) {
                <option [value]="item">{{ item }}</option>
              }
            </select>
          </label>

          <label class="grid gap-1">
            <span class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">
              Orden
            </span>
            <select
              class="rounded-xl border border-dark-border bg-dark-bg px-3 py-2 text-sm text-dark-text"
              [value]="sortBy()"
              (change)="onSortChange($event)"
            >
              @for (item of sortOptions; track item.value) {
                <option [value]="item.value">{{ item.label }}</option>
              }
            </select>
          </label>
        </div>

        <label
          class="mt-4 flex cursor-pointer items-start gap-3 rounded-xl border border-dark-border bg-dark-bg/70 px-3 py-2"
        >
          <input
            class="mt-1 accent-amber-500"
            type="checkbox"
            [checked]="weakSignalsOnly()"
            (change)="onWeakSignalsChange($event)"
          />
          <span>
            <span class="block text-sm text-dark-text">Solo weak signals</span>
            <span class="block text-xs leading-5 text-dark-muted">
              Prioriza clusters pequenos con alta novedad y senales tempranas.
            </span>
          </span>
        </label>
      </section>

      @if (qualityChecks()) {
        <section class="rounded-2xl border border-dark-border bg-dark-surface p-4">
          <h4 class="text-sm font-semibold text-dark-text">Quality Checks</h4>
          <div class="mt-3 grid grid-cols-2 gap-3">
            <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
              <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Coherencia</p>
              <p class="mt-2 text-lg font-semibold text-dark-text">
                {{ qualityChecks()!.cluster_coherence_avg | number:'1.0-0' }}
              </p>
            </div>
            <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
              <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Calidad</p>
              <p class="mt-2 text-lg font-semibold text-dark-text">
                {{ qualityChecks()!.cluster_quality_avg | number:'1.0-0' }}
              </p>
            </div>
            <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
              <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Cobertura tax.</p>
              <p class="mt-2 text-lg font-semibold text-dark-text">
                {{ qualityChecks()!.taxonomy_coverage | number:'1.0-0' }}%
              </p>
            </div>
            <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
              <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">No cluster</p>
              <p class="mt-2 text-lg font-semibold text-dark-text">
                {{ qualityChecks()!.unclustered_ratio | number:'1.0-0' }}%
              </p>
            </div>
            <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
              <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Cobertura</p>
              <p class="mt-2 text-lg font-semibold text-dark-text">
                {{ (qualityChecks()!.cluster_coverage ?? (100 - qualityChecks()!.unclustered_ratio)) | number:'1.0-0' }}%
              </p>
            </div>
            <div class="rounded-xl border border-dark-border bg-dark-bg/70 p-3">
              <p class="text-[11px] uppercase tracking-[0.18em] text-dark-muted">Estabilidad</p>
              <p class="mt-2 text-lg font-semibold text-dark-text">
                {{ (qualityChecks()!.stability_score_avg ?? 0) | number:'1.0-0' }}
              </p>
            </div>
          </div>
        </section>
      }

      <section class="rounded-2xl border border-dark-border bg-dark-surface p-4">
        <div class="flex items-center justify-between gap-3">
          <div>
            <h4 class="text-sm font-semibold text-dark-text">Clusters</h4>
            <p class="mt-1 text-xs text-dark-muted">
              {{ clusters().length }} clusters visibles con el filtro actual.
            </p>
          </div>
        </div>

        <div class="mt-4 space-y-2 max-h-[calc(100vh-26rem)] overflow-y-auto pr-1">
          @for (cluster of clusters(); track cluster.cluster_id) {
            <button
              class="w-full rounded-2xl border p-3 text-left transition cursor-pointer"
              [class]="cardClass(cluster)"
              type="button"
              (click)="onClusterClick(cluster)"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <div class="flex items-center gap-2">
                    <span
                      class="h-2.5 w-2.5 rounded-full"
                      [style.backgroundColor]="categoryColor(cluster.category)"
                    ></span>
                    <p class="text-xs uppercase tracking-[0.18em] text-dark-muted">
                      {{ cluster.category }}
                    </p>
                  </div>
                  <h5 class="mt-1 text-sm font-semibold leading-5 text-dark-text">
                    {{ cluster.label }}
                  </h5>
                  <p class="mt-1 text-xs leading-5 text-dark-muted">
                    {{ cluster.subtitle }}
                  </p>
                </div>
                <span [class]="signalBadge(cluster)">
                  {{ formatStage(cluster.hype_stage) }}
                </span>
              </div>

              <div class="mt-3 flex flex-wrap gap-2">
                @for (kw of cluster.top_keywords.slice(0, 4); track kw) {
                  <span class="rounded-full border border-dark-border bg-dark-bg px-2 py-1 text-[11px] text-dark-muted">
                    {{ kw }}
                  </span>
                }
              </div>

              <div class="mt-3 grid grid-cols-3 gap-2 text-xs">
                <div class="rounded-lg bg-dark-bg/70 px-2 py-2">
                  <p class="text-dark-muted">Impacto</p>
                  <p class="mt-1 font-medium text-dark-text">
                    {{ cluster.impact_score | number:'1.0-0' }}
                  </p>
                </div>
                <div class="rounded-lg bg-dark-bg/70 px-2 py-2">
                  <p class="text-dark-muted">Momentum</p>
                  <p class="mt-1 font-medium text-dark-text">
                    {{ cluster.momentum_score | number:'1.0-0' }}
                  </p>
                </div>
                <div class="rounded-lg bg-dark-bg/70 px-2 py-2">
                  <p class="text-dark-muted">Calidad</p>
                  <p class="mt-1 font-medium text-dark-text">
                    {{ cluster.cluster_quality.score | number:'1.0-0' }}
                  </p>
                </div>
              </div>

              <div class="mt-3 flex items-center justify-between gap-3 text-xs text-dark-muted">
                <span>{{ cluster.item_count }} docs</span>
                @if (cluster.comparative_signal) {
                  <span class="rounded-full border border-dark-border bg-dark-surface px-2 py-1">
                    {{ cluster.comparative_signal.status }} · {{ cluster.comparative_signal.stability_score ?? 0 | number:'1.0-0' }}
                  </span>
                } @else if (cluster.weak_signal_flag) {
                  <span class="rounded-full border border-yellow-500 bg-yellow-100 px-2 py-1 text-yellow-900">
                    weak signal
                  </span>
                }
              </div>
            </button>
          }

          @if (clusters().length === 0) {
            <p class="rounded-xl border border-dark-border bg-dark-bg/60 px-3 py-4 text-center text-sm text-dark-muted">
              No hay clusters para la combinacion de filtros seleccionada.
            </p>
          }
        </div>
      </section>
    </aside>
  `,
})
export class TrendmapSidebarComponent {
  readonly clusters = input<TrendmapCluster[]>([]);
  readonly categories = input<string[]>([]);
  readonly filtersMetadata = input<FiltersMetadata | null>(null);
  readonly selectedCluster = input<TrendmapCluster | null>(null);
  readonly filterCategory = input<string | null>(null);
  readonly filterSourceType = input<string | null>(null);
  readonly filterMaturityStage = input<string | null>(null);
  readonly filterHypeStage = input<LifecycleStage | null>(null);
  readonly filterImpactBand = input<'low' | 'medium' | 'high' | null>(null);
  readonly filterSignalState = input<string | null>(null);
  readonly filterComparativeStatus = input<'new' | 'accelerating' | 'cooling' | 'stable' | null>(null);
  readonly filterNoveltyBand = input<string | null>(null);
  readonly weakSignalsOnly = input(false);
  readonly sortBy = input<ClusterSort>('impact');
  readonly qualityChecks = input<QualityChecks | null>(null);

  readonly clusterSelected = output<TrendmapCluster | null>();
  readonly categoryChanged = output<string | null>();
  readonly sourceTypeChanged = output<string | null>();
  readonly maturityStageChanged = output<string | null>();
  readonly hypeStageChanged = output<LifecycleStage | null>();
  readonly impactBandChanged = output<'low' | 'medium' | 'high' | null>();
  readonly signalStateChanged = output<string | null>();
  readonly comparativeStatusChanged = output<'new' | 'accelerating' | 'cooling' | 'stable' | null>();
  readonly noveltyBandChanged = output<string | null>();
  readonly weakSignalsChanged = output<boolean>();
  readonly sortChanged = output<ClusterSort>();
  readonly clearRequested = output<void>();

  readonly sortOptions = SORT_OPTIONS;
  readonly impactBands = [
    { value: 'high', label: 'Alto (70+)' },
    { value: 'medium', label: 'Medio (45-69)' },
    { value: 'low', label: 'Bajo (<45)' },
  ] as const;

  readonly categoriesList = computed(
    () => this.filtersMetadata()?.categories ?? this.categories(),
  );

  readonly visibleCategories = computed(() => {
    const fromClusters = [...new Set(this.clusters().map((cluster) => cluster.category))];
    return fromClusters.length > 0 ? fromClusters : this.categoriesList();
  });

  readonly sourceTypes = computed(
    () => this.filtersMetadata()?.source_types ?? [],
  );

  readonly maturityStages = computed(
    () => this.filtersMetadata()?.maturity_stages ?? [],
  );

  readonly hypeStages = computed(
    () => this.filtersMetadata()?.hype_stages ?? [],
  );

  readonly signalStates = computed(
    () => this.filtersMetadata()?.signal_states ?? [],
  );

  readonly comparativeStatuses = computed(
    () => this.filtersMetadata()?.comparative_statuses ?? [],
  );

  readonly noveltyBands = computed(
    () => this.filtersMetadata()?.novelty_bands ?? [],
  );

  onClusterClick(cluster: TrendmapCluster): void {
    const current = this.selectedCluster();
    this.clusterSelected.emit(current?.cluster_id === cluster.cluster_id ? null : cluster);
  }

  onCategoryChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.categoryChanged.emit(value || null);
  }

  onSourceTypeChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.sourceTypeChanged.emit(value || null);
  }

  onMaturityStageChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.maturityStageChanged.emit(value || null);
  }

  onHypeStageChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value as LifecycleStage | '';
    this.hypeStageChanged.emit(value || null);
  }

  onImpactBandChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value as 'low' | 'medium' | 'high' | '';
    this.impactBandChanged.emit(value || null);
  }

  onWeakSignalsChange(event: Event): void {
    this.weakSignalsChanged.emit((event.target as HTMLInputElement).checked);
  }

  onSignalStateChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.signalStateChanged.emit(value || null);
  }

  onComparativeStatusChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value as 'new' | 'accelerating' | 'cooling' | 'stable' | '';
    this.comparativeStatusChanged.emit(value || null);
  }

  onNoveltyBandChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.noveltyBandChanged.emit(value || null);
  }

  onSortChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value as ClusterSort;
    this.sortChanged.emit(value);
  }

  formatStage(stage: string): string {
    return stage.replaceAll('_', ' ');
  }

  cardClass(cluster: TrendmapCluster): string {
    const isSelected = this.selectedCluster()?.cluster_id === cluster.cluster_id;
    if (isSelected) {
      return 'border-yellow-500 bg-yellow-50';
    }
    return 'border-dark-border bg-white hover:border-yellow-400 hover:bg-yellow-50';
  }

  signalBadge(cluster: TrendmapCluster): string {
    const base =
      'inline-flex rounded-full border px-2 py-1 text-[10px] font-medium leading-none ';
    if (cluster.weak_signal_flag) {
      return base + 'border-yellow-500 bg-yellow-100 text-yellow-900';
    }
    if (cluster.hype_stage === 'productive_adoption') {
      return base + 'border-emerald-500 bg-emerald-50 text-emerald-700';
    }
    if (cluster.hype_stage === 'correction') {
      return base + 'border-rose-500 bg-rose-50 text-rose-700';
    }
    return base + 'border-sky-500 bg-sky-50 text-sky-700';
  }

  categoryColor(category: string): string {
    const palette = ['#38bdf8', '#f59e0b', '#34d399', '#fb7185', '#818cf8', '#f97316'];
    const hash = [...category].reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return palette[hash % palette.length];
  }
}
