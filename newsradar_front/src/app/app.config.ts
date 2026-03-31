import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withFetch } from '@angular/common/http';

import { routes } from './app.routes';
import { API_BASE_URL } from './config/api.token';
import { environment } from './config/environment';
import { RIESGOS_API, VIGILANCIA_API, TRENDMAP_API } from './infrastructure/noticias/services/noticias-api.token';
import { RiesgosHttpService } from './infrastructure/noticias/services/riesgos-http.service';
import { VigilanciaHttpService } from './infrastructure/noticias/services/vigilancia-http.service';
import { TrendmapHttpService } from './infrastructure/noticias/services/trendmap-http.service';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(withFetch()),
    { provide: API_BASE_URL, useValue: environment.apiBaseUrl },
    { provide: RIESGOS_API, useClass: RiesgosHttpService },
    { provide: VIGILANCIA_API, useClass: VigilanciaHttpService },
    { provide: TRENDMAP_API, useClass: TrendmapHttpService },
  ],
};
