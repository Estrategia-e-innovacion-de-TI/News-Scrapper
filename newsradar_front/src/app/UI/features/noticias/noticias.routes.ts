import { InjectionToken } from '@angular/core';
import { Routes } from '@angular/router';
import { NoticiasComponent } from './noticias.component';

export const NOTICIAS_ROUTE_PREFIX = new InjectionToken<string>('NOTICIAS_ROUTE_PREFIX', {
  providedIn: 'root',
  factory: () => 'noticias',
});

export const NOTICIAS_ROUTES: Routes = [
  {
    path: '',
    component: NoticiasComponent,
    children: [
      { path: '', redirectTo: 'riesgos', pathMatch: 'full' },
      {
        path: 'riesgos',
        loadComponent: () =>
          import('./components/riesgos/riesgos.component').then((m) => m.RiesgosComponent),
      },
      {
        path: 'vigilancia',
        loadComponent: () =>
          import('./components/vigilancia/vigilancia.component').then((m) => m.VigilanciaComponent),
      },
      {
        path: 'trendmap',
        loadComponent: () =>
          import('./components/trendmap/trendmap.component').then((m) => m.TrendmapComponent),
      },
    ],
  },
];
