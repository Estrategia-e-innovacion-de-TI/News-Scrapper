import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [RouterLink],
  template: `
    <header class="relative w-full">
      <nav
        class="w-full"
        style="background-color: #2c2a29; box-shadow: 0px 2px 4px rgba(0,0,0,0.1);"
      >
        <div class="container mx-auto px-6 py-4 flex justify-center items-center">
          <ul class="flex justify-center items-center space-x-8 text-lg">
            <li class="flex items-center">
              <a
                routerLink="/noticias"
                class="text-white hover:bg-white hover:text-black px-4 py-2 rounded transition-colors duration-200"
              >
                News Radar
              </a>
            </li>
          </ul>
        </div>
      </nav>
    </header>
  `,
})
export class HeaderComponent {}
