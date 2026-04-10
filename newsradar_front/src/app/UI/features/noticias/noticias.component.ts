import { Component, signal, ViewEncapsulation } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

interface TabDef {
  id: string;
  label: string;
  group?: 'trends' | 'risks';
  route?: string;
  externalUrl?: string;
}

const TABS: TabDef[] = [
  { id: 'home', label: 'Inicio', route: 'home' },
  { id: 'trendmap', label: 'Mapa de tendencias', route: 'trendmap', group: 'trends' },
  { id: 'subscriptions', label: 'Suscripciones', route: 'subscriptions', group: 'trends' },
  { id: 'aras', label: 'ARAS y riesgos', route: 'aras', group: 'risks' },
  { id: 'riskmap', label: 'Mapa de riesgos', route: 'riskmap', group: 'risks' },
  { id: 'navi', label: 'Conoce mas sobre Navi', externalUrl: 'https://d25asr8tvzjrih.cloudfront.net/' },
];

@Component({
  selector: 'app-noticias',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  encapsulation: ViewEncapsulation.Emulated,
  template: `
    <div class="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      <div class="mb-3 flex flex-wrap gap-2 text-xs font-semibold tracking-wide">
        <span class="rounded-full border border-sky-300 bg-sky-50 px-3 py-1 text-sky-800">
          Vigilancia de tendencias tecnologicas
        </span>
        <span class="rounded-full border border-rose-300 bg-rose-50 px-3 py-1 text-rose-800">
          Vigilancia de riesgos emergentes
        </span>
      </div>
      <nav
        class="mb-6 flex flex-wrap gap-2 rounded-2xl border border-dark-border bg-white p-2 shadow-sm"
        role="tablist"
        aria-label="Secciones principales"
      >
        @for (tab of tabs; track tab.id) {
          @if (tab.externalUrl) {
            <a
              [href]="tab.externalUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="ml-auto rounded-xl border border-yellow-300 bg-yellow-50 px-4 py-2 text-sm font-semibold text-dark-text transition-colors hover:bg-yellow-200"
              role="tab"
              aria-selected="false"
            >
              {{ tab.label }}
            </a>
          } @else {
            <a
              [routerLink]="tab.route"
              [routerLinkActive]="tabActiveClasses(tab)"
              [class]="tabBaseClasses(tab)"
              role="tab"
              [attr.aria-selected]="activeTab() === tab.id"
              (click)="activeTab.set(tab.id)"
            >
              {{ tab.label }}
            </a>
          }
        }
      </nav>
      <router-outlet />
    </div>
  `,
})
export class NoticiasComponent {
  readonly tabs = TABS;
  readonly activeTab = signal('home');

  tabBaseClasses(tab: TabDef): string {
    const base = 'rounded-xl px-4 py-2 text-sm font-medium transition-colors';

    if (tab.group === 'trends') {
      return `${base} border border-sky-200 bg-sky-50/70 text-sky-800 hover:bg-sky-100`;
    }

    if (tab.group === 'risks') {
      return `${base} border border-rose-200 bg-rose-50/70 text-rose-800 hover:bg-rose-100`;
    }

    return `${base} text-dark-muted hover:bg-yellow-50 hover:text-dark-text`;
  }

  tabActiveClasses(tab: TabDef): string {
    if (tab.group === 'trends') {
      return 'bg-sky-200 border-sky-300 text-sky-950 shadow-sm';
    }

    if (tab.group === 'risks') {
      return 'bg-rose-200 border-rose-300 text-rose-950 shadow-sm';
    }

    return 'bg-yellow-300 text-dark-text shadow-sm';
  }
}
