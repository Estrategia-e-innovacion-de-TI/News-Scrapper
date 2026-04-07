import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [RouterLink],
  template: `
    <header class="sticky top-0 z-40 w-full border-b border-dark-border bg-white/95 shadow-sm backdrop-blur">
      <nav class="w-full">
        <div class="mx-auto flex max-w-7xl items-center justify-between gap-6 px-6 py-3">
          <a routerLink="/noticias" class="flex min-w-0 items-center gap-4" aria-label="Ir al inicio">
            <span class="flex h-14 w-72 items-center overflow-hidden rounded-xl border border-dark-border bg-white px-2 shadow-sm">
              <img
                src="/images/logo.png"
                alt="Bancolombia - Framework de Innovacion TI"
                class="h-full w-full object-contain object-center"
              />
            </span>
            <span class="hidden min-w-0 sm:block">
              <span class="block text-sm font-semibold tracking-tight text-dark-text">
                Radar de Noticias
              </span>
              <span class="block text-xs text-dark-muted">
                Analitica documental e inteligencia de tendencias
              </span>
            </span>
          </a>

          <a
            routerLink="/noticias"
            class="rounded-full border border-dark-border bg-dark-bg px-4 py-2 text-sm font-medium text-dark-text transition hover:border-yellow-400 hover:bg-yellow-50"
          >
            Panel principal
          </a>
        </div>
      </nav>
    </header>
  `,
})
export class HeaderComponent {}
