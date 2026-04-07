import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-noticias-home',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="space-y-6">
      <section class="overflow-hidden rounded-3xl border border-dark-border bg-white shadow-sm">
        <div class="grid gap-0 lg:grid-cols-[1.25fr_0.75fr]">
          <div class="p-6 sm:p-8">
            <p class="text-xs font-semibold uppercase tracking-[0.22em] text-dark-muted">
              Radar de Noticias Bancolombia
            </p>
            <h1 class="mt-4 max-w-3xl text-3xl font-semibold tracking-tight text-dark-text sm:text-4xl">
              Inteligencia documental para anticipar tendencias, senales y riesgos.
            </h1>
            <p class="mt-4 max-w-3xl text-sm leading-7 text-dark-muted">
              Este artefacto de Navi consolida fuentes de noticias, papers y reportes para convertir
              vigilancia tecnologica en snapshots accionables. La analitica ocurre en backend y el
              frontend presenta lectura ejecutiva, clusters, evidencias y trazabilidad.
            </p>

            <div class="mt-6 flex flex-wrap gap-3">
              <a
                routerLink="../trendmap"
                class="rounded-full bg-yellow-300 px-5 py-2.5 text-sm font-semibold text-dark-text shadow-sm transition hover:bg-yellow-200"
              >
                Ver mapa de tendencias
              </a>
              <a
                routerLink="../riskmap"
                class="rounded-full border border-dark-border bg-dark-bg px-5 py-2.5 text-sm font-semibold text-dark-text transition hover:border-yellow-400 hover:bg-yellow-50"
              >
                Ver mapa de riesgos
              </a>
            </div>
          </div>

          <div class="border-t border-dark-border bg-gradient-to-br from-yellow-50 via-white to-sky-50 p-6 lg:border-l lg:border-t-0">
            <div class="rounded-3xl border border-white/70 bg-white/85 p-5 shadow-sm">
              <p class="text-xs font-semibold uppercase tracking-[0.18em] text-dark-muted">
                Flujo operativo
              </p>
              <div class="mt-4 space-y-3 text-sm text-dark-muted">
                <p><span class="font-semibold text-dark-text">1.</span> Ingesta noticias, papers y fuentes especializadas.</p>
                <p><span class="font-semibold text-dark-text">2.</span> Normaliza texto, score, fuente y senales temporales.</p>
                <p><span class="font-semibold text-dark-text">3.</span> Construye snapshots JSON para tendencias y riesgos.</p>
                <p><span class="font-semibold text-dark-text">4.</span> Expone clusters, insights, recomendaciones y evidencia.</p>
              </div>
              <a
                routerLink="../tech-watch"
                class="mt-5 inline-flex rounded-full border border-dark-border bg-white px-4 py-2 text-xs font-semibold text-dark-text transition hover:border-yellow-400 hover:bg-yellow-50"
              >
                Administrar ingesta
              </a>
            </div>
          </div>
        </div>
      </section>

      <div class="grid gap-4 md:grid-cols-3">
        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h2 class="text-sm font-semibold text-dark-text">Mapa de tendencias</h2>
          <p class="mt-2 text-sm leading-6 text-dark-muted">
            Agrupa evidencia documental en clusters interpretables, priorizados por impacto,
            madurez, momentum y novedad.
          </p>
        </section>
        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h2 class="text-sm font-semibold text-dark-text">Mapa de riesgos</h2>
          <p class="mt-2 text-sm leading-6 text-dark-muted">
            Reutiliza la base analitica para detectar senales de riesgo, severidad,
            persistencia y documentos representativos.
          </p>
        </section>
        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h2 class="text-sm font-semibold text-dark-text">Snapshot-driven</h2>
          <p class="mt-2 text-sm leading-6 text-dark-muted">
            La interfaz no recalcula analitica: consume snapshots versionados para mantener
            trazabilidad, reproducibilidad y separacion backend/frontend.
          </p>
        </section>
      </div>
    </div>
  `,
})
export class NoticiasHomeComponent {}
