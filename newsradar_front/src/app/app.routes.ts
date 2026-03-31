import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: 'noticias',
    loadChildren: () =>
      import('./UI/features/noticias/noticias.routes').then(
        (m) => m.NOTICIAS_ROUTES
      ),
  },
  {
    path: '',
    redirectTo: 'noticias',
    pathMatch: 'full',
  },
  {
    path: '**',
    redirectTo: 'noticias',
    pathMatch: 'full',
  },
];
