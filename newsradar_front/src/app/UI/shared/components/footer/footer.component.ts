import { Component } from '@angular/core';

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [],
  template: `
    <footer class="mt-auto border-t border-dark-border bg-white py-6">
      <div class="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-6">
        <p class="text-sm text-dark-muted">
          &copy; 2026 Radar Estrategico TI Bancolombia
        </p>
        <p class="text-xs text-dark-muted">
          ARQUITECTURA INNOVACION TI
        </p>
      </div>
    </footer>
  `,
})
export class FooterComponent {}
