import { Component, signal, ViewEncapsulation } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

interface TabDef {
  id: string;
  label: string;
  route: string;
}

const TABS: TabDef[] = [
  { id: 'tech-watch', label: 'Vigilancia Tecnologica', route: 'tech-watch' },
  { id: 'trendmap', label: 'Trend Mapping', route: 'trendmap' },
  { id: 'subscriptions', label: 'Subscripciones', route: 'subscriptions' },
  { id: 'aras', label: 'ARAS / Riesgos', route: 'aras' },
  { id: 'riskmap', label: 'Risk Mapping', route: 'riskmap' },
];

@Component({
  selector: 'app-noticias',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  encapsulation: ViewEncapsulation.Emulated,
  template: `
    <div class="p-4">
      <nav class="flex flex-wrap gap-1 border-b border-gray-200 mb-6" role="tablist" aria-label="Secciones principales">
        @for (tab of tabs; track tab.id) {
          <a
            [routerLink]="tab.route"
            routerLinkActive="border-b-2 border-yellow-400 text-black font-semibold"
            class="px-4 py-2 text-sm text-gray-600 hover:text-black transition-colors"
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
