import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [RouterLink],
  template: `
    <header class="sticky top-0 z-40 w-full border-b border-dark-border bg-white/95 shadow-sm backdrop-blur">
      <div class="h-1 w-full bg-gradient-to-r from-yellow-300 via-sky-300 to-orange-400"></div>
      <nav class="w-full">
        <div class="mx-auto flex max-w-7xl items-center justify-between gap-6 px-6 py-4">
          <a routerLink="/noticias" class="flex min-w-0 items-center gap-4" aria-label="Ir al inicio">
            <span class="flex h-14 w-52 items-center overflow-hidden rounded-2xl border border-dark-border bg-white px-3 shadow-sm sm:h-16 sm:w-72 lg:w-[22rem]">
              <img
                src="/images/logo.png"
                alt="Bancolombia - Framework de Innovacion TI"
                class="h-full w-full object-contain object-center"
              />
            </span>
            <span class="hidden min-w-0 sm:block">
              <span class="block text-base font-semibold tracking-tight text-dark-text">
                Radar de Noticias
              </span>
              <span class="block text-xs text-dark-muted">
                Subproducto temporal del framework de innovacion Navi
              </span>
            </span>
          </a>

          <div class="hidden items-center gap-3 md:flex">
            <a
              href="https://d25asr8tvzjrih.cloudfront.net/"
              target="_blank"
              rel="noopener noreferrer"
              class="rounded-full border border-yellow-300 bg-yellow-50 px-4 py-2 text-sm font-semibold text-dark-text transition hover:bg-yellow-200"
            >
              Conoce mas de Navi
            </a>
            <a
              routerLink="/noticias"
              class="rounded-full border border-dark-border bg-dark-bg px-4 py-2 text-sm font-medium text-dark-text transition hover:border-yellow-400 hover:bg-yellow-50"
            >
              Panel principal
            </a>
          </div>
        </div>
      </nav>
    </header>
  `,
})
export class HeaderComponent {}
