import { Component } from '@angular/core';

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [],
  template: `
    <footer class="bg-black text-neutral py-8 mt-auto">
      <div class="max-w-6xl mx-auto px-4 text-center">
        <div class="mt-4 bg-black p-4 rounded">
          <p class="text-sm text-secondary-light">
            &copy; 2025 News Radar — Arquitectura Innovación TI
          </p>
        </div>
      </div>
    </footer>
  `,
})
export class FooterComponent {}
