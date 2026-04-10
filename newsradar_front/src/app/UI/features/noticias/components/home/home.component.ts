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
              Radar Estrategico TI Bancolombia
            </p>
            <h1 class="mt-4 max-w-3xl text-3xl font-semibold tracking-tight text-dark-text sm:text-4xl">
              Un radar para convertir ruido externo en decisiones estrategicas.
            </h1>
            <p class="mt-4 max-w-3xl text-sm leading-7 text-dark-muted">
              Esta herramienta de Navi te ayuda a identificar que temas estan tomando fuerza,
              cuales conviene observar con mayor atencion, que riesgos estan emergiendo y
              donde vale la pena concentrar conversaciones clave. El resultado no es solo una
              lista de noticias: es una lectura clara y accionable, con evidencia, agrupaciones
              tematicas, recomendaciones y trazabilidad documental.
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
                Que puedes obtener
              </p>
              <div class="mt-4 space-y-3 text-sm text-dark-muted">
                <p><span class="font-semibold text-dark-text">Oportunidades:</span> temas emergentes que pueden orientar exploracion, pilotos y apuestas de negocio.</p>
                <p><span class="font-semibold text-dark-text">Priorizacion:</span> lectura por impacto, madurez, dinamica de crecimiento y novedad para separar senales fuertes del ruido.</p>
                <p><span class="font-semibold text-dark-text">Riesgos:</span> indicios tempranos de ciberseguridad, regulacion, fraude, reputacion u operacion.</p>
                <p><span class="font-semibold text-dark-text">Evidencia:</span> documentos representativos, fuentes, analisis y recomendaciones para conversar con contexto.</p>
              </div>
              <a
                routerLink="../tech-watch"
                class="mt-5 inline-flex rounded-full border border-dark-border bg-white px-4 py-2 text-xs font-semibold text-dark-text transition hover:border-yellow-400 hover:bg-yellow-50"
              >
                Gestionar fuentes y ejecuciones
              </a>
            </div>
          </div>
        </div>
      </section>

      <div class="grid gap-4 md:grid-cols-3">
        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h2 class="text-sm font-semibold text-dark-text">Enfocar la atencion</h2>
          <p class="mt-2 text-sm leading-6 text-dark-muted">
            El radar organiza indicios dispersos en temas coherentes para mostrar que esta
            creciendo, que se esta consolidando y que aun requiere seguimiento cercano.
          </p>
        </section>
        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h2 class="text-sm font-semibold text-dark-text">Decidir con claridad</h2>
          <p class="mt-2 text-sm leading-6 text-dark-muted">
            Cada grupo tematico incluye documentos representativos, palabras clave,
            interpretacion, recomendacion y justificacion para facilitar discusiones
            ejecutivas y decisiones de portafolio.
          </p>
        </section>
        <section class="rounded-2xl border border-dark-border bg-dark-surface p-5">
          <h2 class="text-sm font-semibold text-dark-text">Anticipar riesgos</h2>
          <p class="mt-2 text-sm leading-6 text-dark-muted">
            La misma base permite observar riesgos emergentes, severidad, persistencia y
            dinamica de crecimiento para priorizar conversaciones entre tecnologia,
            negocio y control.
          </p>
        </section>
      </div>
    </div>
  `,
})
export class NoticiasHomeComponent {}
