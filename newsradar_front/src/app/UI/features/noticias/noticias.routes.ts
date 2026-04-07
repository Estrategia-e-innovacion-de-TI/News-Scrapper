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
      { path: '', redirectTo: 'home', pathMatch: 'full' },
      {
        path: 'home',
        loadComponent: () =>
          import('./components/home/home.component').then((m) => m.NoticiasHomeComponent),
      },
      {
        path: 'tech-watch',
        loadComponent: () =>
          import('./components/tech-watch/tech-watch.component').then((m) => m.TechWatchComponent),
      },
      {
        path: 'trendmap',
        loadComponent: () =>
          import('./components/trendmap/trendmap.component').then((m) => m.TrendmapComponent),
      },
      {
        path: 'subscriptions',
        loadComponent: () =>
          import('./components/subscriptions/subscriptions.component').then((m) => m.SubscriptionsComponent),
      },
      {
        path: 'aras',
        loadComponent: () =>
          import('./components/riesgos/riesgos.component').then((m) => m.RiesgosComponent),
      },
      {
        path: 'riskmap',
        loadComponent: () =>
          import('./components/riskmap/riskmap.component').then((m) => m.RiskmapComponent),
      },
      {
        path: 'riesgos',
        redirectTo: 'aras',
        pathMatch: 'full',
      },
      {
        path: 'vigilancia',
        redirectTo: 'tech-watch',
        pathMatch: 'full',
      },
    ],
  },
];
