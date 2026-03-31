import { Component } from '@angular/core';
import { VigilanciaComponent } from '../vigilancia/vigilancia.component';

@Component({
  selector: 'app-subscriptions-view',
  standalone: true,
  imports: [VigilanciaComponent],
  template: `<app-vigilancia />`,
})
export class SubscriptionsComponent {}
