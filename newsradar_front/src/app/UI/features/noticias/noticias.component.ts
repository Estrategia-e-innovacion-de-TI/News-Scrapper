import { Component, signal, ViewEncapsulation } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

interface TabDef {
  id: string;
  label: string;
  route: string;
}

const TABS: TabDef[] = [
  { id: 'tech-watch', label: 'Vigilancia tecnologica', route: 'tech-watch' },
  { id: 'trendmap', label: 'Mapa de tendencias', route: 'trendmap' },
  { id: 'subscriptions', label: 'Suscripciones', route: 'subscriptions' },
  { id: 'aras', label: 'ARAS y riesgos', route: 'aras' },
  { id: 'riskmap', label: 'Mapa de riesgos', route: 'riskmap' },
];

@Component({
  selector: 'app-noticias',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  encapsulation: ViewEncapsulation.Emulated,
  template: `
    <div class="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      <nav
        class="mb-6 flex flex-wrap gap-2 rounded-2xl border border-dark-border bg-white p-2 shadow-sm"
        role="tablist"
        aria-label="Secciones principales"
      >
        @for (tab of tabs; track tab.id) {
          <a
            [routerLink]="tab.route"
            routerLinkActive="bg-yellow-300 text-dark-text shadow-sm"
            class="rounded-xl px-4 py-2 text-sm font-medium text-dark-muted transition-colors hover:bg-yellow-50 hover:text-dark-text"
            role="tab"
            [attr.aria-selected]="activeTab() === tab.id"
            (click)="activeTab.set(tab.id)"
          >
            {{ tab.label }}
          </a>
        }
      </nav>
      <router-outlet />
    </div>
  `,
})
export class NoticiasComponent {
  readonly tabs = TABS;
  readonly activeTab = signal('tech-watch');
}
